import os
import time
from pathlib import Path
from typing import Dict, List, Callable, Any, Optional, Tuple, Any
import traceback
from service.log import get_logger
from . import prompt
from . import llm_helper
import re
from service import localization
from service import glossary

logger = get_logger("LightVT")

def parse_srt(content: str) -> List[Dict[str, str]]:
    """解析SRT文件内容为字幕列表"""
    subtitles = []
    blocks = content.strip().split("\n\n")
    
    for block in blocks:
        lines = block.split("\n")
        if len(lines) >= 3:
            subtitle_id = lines[0]
            time_code = lines[1]
            text = "\n".join(lines[2:])
            
            subtitles.append({
                "id": subtitle_id,
                "time_code": time_code,
                "text": text
            })
    
    return subtitles

def format_srt(subtitles: List[Dict[str, str]]) -> str:
    """将字幕列表格式化为SRT内容"""
    return "\n\n".join([
        f"{subtitle['id']}\n{subtitle['time_code']}\n{subtitle['text']}"
        for subtitle in subtitles
    ])

def chunk_subtitles_with_context(
    subtitles: List[Dict[str, str]], 
    max_chunk_size: int = 10,
    context_size: int = 2  # 前后各保留2条作为上下文
) -> List[List[Dict[str, str]]]:
    """分块时保留上下文信息"""
    chunks = []
    
    for i in range(0, len(subtitles), max_chunk_size):
        # 计算上下文范围
        start_context = max(0, i - context_size)
        end_context = min(len(subtitles), i + max_chunk_size + context_size)
        
        # 主要翻译部分
        main_chunk = subtitles[i:i + max_chunk_size]
        
        main_indices = None
        if i == 0:
            main_indices = list(range(0, len(main_chunk)))
        elif i + max_chunk_size >= len(subtitles):
            # 如果是最后一块，可能需要调整索引
            main_indices = list(range(context_size, context_size + len(main_chunk)))
        else:
            main_indices = list(range(context_size, context_size + len(main_chunk)))
        
        # 完整上下文（用于翻译参考）
        full_context = subtitles[start_context:end_context]
        
        chunks.append({
            'main': main_chunk,      # 需要翻译的主要部分
            'context': full_context, # 完整上下文
            'start_idx': i,          # 在原文中的起始位置
            'context_size': context_size,  # 上下文大小
            'main_indices': main_indices  # 主要翻译部分的索引
        })
    
    return chunks

def apply_translation_to_chunk(
    chunk: Dict[str, Any], 
    translated_text: str,
    log_fn: Callable[[str], None] = print
) -> List[Dict[str, str]]:
    """将翻译结果应用到字幕块"""
    # 分割翻译结果
    translated_lines = llm_helper.parse_translation_text(translated_text)
    
    main_chunk = chunk["main"]
    
    # 确保翻译行数与原始字幕匹配
    if len(translated_lines) < len(main_chunk):
        logger.warning(f"警告: 翻译行数 ({len(translated_lines)}) 少于原始字幕行数 ({len(main_chunk)})，\n 翻译文本: {translated_text}, \n 原始字幕: {llm_helper.prepare_text_for_translation(main_chunk)}")
        while len(translated_lines) < len(main_chunk):
            translated_lines.append(localization.get("msg_translation_missing"))
    
    # 将翻译应用到字幕
    return [
        {**subtitle, "text": translated_lines[i] if i < len(translated_lines) else subtitle["text"]}
        for i, subtitle in enumerate(main_chunk)
    ]
    
def translate_srt_file(
    input_path: str, 
    output_path: str, 
    model_path: str, 
    source_lang: str, 
    target_lang: str,
    n_gpu_layers: int = 0,
    chunk_size: int = 10,
    context_size: int = 2,
    reflection_enabled: bool = False,
    log_fn: Callable[[str], None] = print,
    stop_event: Optional[Any] = None
) -> bool:
    # 检查停止信号
    if stop_event and stop_event.is_set():
        log_fn(localization.get("log_processing_stopped"))
        return False
    
    # 读取输入文件
    log_fn(f"{localization.get('log_reading_subtitle_file')} {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return translate_srt_text(
        input_text=content,
        output_path=output_path,
        model_path=model_path,
        source_lang=source_lang,
        target_lang=target_lang,
        n_gpu_layers=n_gpu_layers,
        chunk_size=chunk_size,
        context_size=context_size,
        reflection_enabled=reflection_enabled,
        log_fn=log_fn,
        stop_event=stop_event
    )

def translate_srt_text(
    input_text: str, 
    output_path: str, 
    model_path: str, 
    source_lang: str, 
    target_lang: str,
    n_gpu_layers: int = 0,
    chunk_size: int = 10,
    context_size: int = 2,
    reflection_enabled: bool = True,
    log_fn: Callable[[str], None] = print,
    stop_event: Optional[Any] = None
) -> bool:
    """翻译SRT文件的主函数"""
    try:
        # 解析SRT
        subtitles = parse_srt(input_text)
        log_fn(localization.get("log_parsed_subtitles").format(subtitles_length=len(subtitles)))
        
        # 检测术语表
        if glossary.is_empty():
            log_fn(localization.get("log_no_glossary"))
            glossary.load_generated_glossary(
                subtitle_text=input_text,
                target_language=target_lang,
                model_path=model_path,
                n_gpu_layers=n_gpu_layers,
                stop_event=stop_event,
                update_progress=log_fn
            )
        else:
            log_fn(localization.get("log_glossary_found"))
        
        # 初始化LLM
        log_fn(localization.get("log_initializing_translation_model").format(n_gpu_layers=n_gpu_layers))
        llm = llm_helper.create_llm(model_path, n_gpu_layers)
        
        # 生成系统提示
        system_prompt = prompt.generate_system_prompt(source_lang, target_lang)
        
        # 分块处理
        chunks = chunk_subtitles_with_context(subtitles, chunk_size,context_size)
        log_fn(localization.get("log_chunking_subtitles").format(chunks_length=len(chunks)))
        
        # 翻译每个块
        translated_subtitles = []
        for i, chunk in enumerate(chunks):
            if stop_event and stop_event.is_set():
                log_fn(localization.get("log_received_stop_signal"))
                return False
            
            log_fn(localization.get("log_translating_chunk").format(chunk_index=i+1, total_chunks=len(chunks)))
            
            # 翻译
            translated_text = llm_helper.translate_text(
                llm, chunk, system_prompt, log_fn=log_fn
            )
            
            # 只有在启用反思时才进行改良
            if reflection_enabled:
                log_fn(localization.get("log_reflection_improvement"))
                
                #改良意见
                recommendation = llm_helper.ask_for_recommendation(
                    llm,
                    chunk,
                    translated_text,
                    target_lang=target_lang,
                    log_fn=log_fn
                )
                
                #改良翻译
                translated_text = llm_helper.improve_translation_with_recommendation(
                    llm,
                    chunk,
                    translated_text,
                    recommendation,
                    system_prompt,
                    log_fn=log_fn
                )
            else:
                log_fn(localization.get("log_reflection_disabled"))

            #review翻译
            translated_text = llm_helper.review_translation(
                llm,
                chunk,
                translated_text,
                system_prompt,
                log_fn=log_fn
            )
            
            
            # 应用翻译结果
            translated_chunk = apply_translation_to_chunk(chunk, translated_text,log_fn)
            translated_subtitles.extend(translated_chunk)
            
            # 可选休息以防止API速率限制
            if i < len(chunks) - 1:
                time.sleep(0.5)
        
        # 格式化并保存结果
        output_content = format_srt(translated_subtitles)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        log_fn(localization.get("log_translation_completed").format(output_path=output_path))
        return True
        
    except Exception as e:
        log_fn(localization.get("log_translation_error").format(error_message=str(e), traceback=traceback.format_exc()))
        return False