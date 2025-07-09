from typing import Dict, List, Callable, Any, Optional, Tuple, Any
from . import prompt
import re
from service.log import get_logger
from service import localization
from llama_cpp import Llama

logger = get_logger("LightVT")

def prepare_text_for_translation(chunk: List[Dict[str, str]]) -> str:
    """准备要翻译的字幕块文本"""
    return "\n".join([f"{i+1}. {s['text']}" for i, s in enumerate(chunk)])

def parse_translation_text(translated_text: str) -> List[str]:
    """解析翻译文本，提取每条内容（支持 [[编号]] 格式）"""
    lines = translated_text.strip().split("\n")
    parsed_lines = []
    
    current_line = ""
    for line in lines:
        line = line.strip()
        # 检查是否是 [[编号]] 开头的行
        if line.startswith("[[") and line.endswith("]]") and line[2:-2].isdigit():
            # 如果当前行有内容，保存到结果中
            if current_line:
                parsed_lines.append(current_line.strip())
            # 开始新的字幕内容
            current_line = ""
        else:
            # 拼接当前行到字幕内容
            current_line += " " + line
    
    # 保存最后一条字幕内容
    if current_line:
        parsed_lines.append(current_line.strip())
    
    return parsed_lines

def create_llm(model_path: str, n_gpu_layers: int = 0, n_ctx: int = 4096) -> Any:
    """创建并返回LLM模型实例"""
    return Llama(
        model_path=model_path,
        n_gpu_layers=n_gpu_layers,
        n_ctx=n_ctx
    )

def translate_text(
    llm: Any, 
    chunk: Dict[str, Any],
    system_prompt: str, 
    max_tokens: int = 2048, 
    temperature: float = 0.2, 
    log_fn: Callable[[str], None] = print
) -> str:
    """使用LLM翻译文本"""
    main_chunk = chunk['main']
    full_context = chunk['context']

    # 确定主要翻译的索引范围
    main_indices = chunk['main_indices']

    # 要翻译的文本长度
    main_chunk_text_length = sum(len(s['text']) for s in main_chunk)

    log_fn(localization.get("msg_translating_text").format(characters_count=main_chunk_text_length))
    
    # 生成上下文感知的提示
    user_prompt =prompt.generate_translation_prompt(full_context, main_indices)
    
    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=max_tokens,
        temperature=temperature
    )
    
    translated_text = response["choices"][0]["message"]["content"].strip()
    #删除<think>标签
    translated_text = re.sub(r"<think>[\s\S]*?</think>", "", translated_text)
    
    log_fn(localization.get("msg_translation_complete")
        .format(result_length=len(translated_text)))
    logger.info(f"翻译提示词:\n{user_prompt}") 
    logger.info(f"翻译结果：\n{translated_text}")
    
    return translated_text

def ask_for_recommendation(
        llm: Any,
        chunk: Dict[str, Any],
        translated_text: str,
        target_lang: str, 
        max_tokens: int = 2048, 
        temperature: float = 0.1, 
        log_fn: Callable[[str], None] = print) -> str:
    """改进翻译结果"""
    # 这里可以添加更复杂的改良逻辑
    full_context = chunk['context']

    # 确定主要翻译的索引范围
    main_indices = chunk['main_indices']
    
    review_system_prompt = prompt.generate_recommendation_system_prompt(target_lang)
    user_prompt = prompt.generate_recommendation_prompt(full_context,main_indices,translated_text)
    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": review_system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=max_tokens,
        temperature=temperature
    )
    # 目前仅返回原翻译结果
    recommendation = response["choices"][0]["message"]["content"].strip()
    
    # 删除<think>标签
    recommendation = re.sub(r"<think>[\s\S]*?</think>", "", recommendation)
    
    log_fn(localization.get("msg_improvement_prompt_generated"))
    logger.info(f"改进建议提示词：{user_prompt}")
    logger.info(f"改进建议: {recommendation}")
    return recommendation

def review_translation(
        llm: Any,
        chunk: Dict[str, Any],
        translated_text: str,
        system_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        log_fn: Callable[[str], None] = print) -> str:
    """改进翻译结果"""
    full_context = chunk['context']
    
    main_indices = chunk['main_indices']
    
    # 解析译文，根据序号提取条数，并与main_indices条数相比对
    translated_lines = parse_translation_text(translated_text)
    
    if len(translated_lines) != len(main_indices):
        user_prompt = prompt.generate_review_translation_prompt(full_context,main_indices,translated_text)
        # user_prompt =prompt.generate_translation_prompt(full_context, main_indices)
        response = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        improved_translation = response["choices"][0]["message"]["content"].strip()
        
        # 删除<think>标签
        improved_translation = re.sub(r"<think>[\s\S]*?</think>", "", improved_translation)
        
        src_text = "\n".join([f"{i+1}. {s['text']}" for i, s in enumerate(chunk["main"])])
        logger.info("原文与译文条数不匹配")
        logger.info(f"review改进翻译提示词：{user_prompt}")
        logger.info(f"原文:{src_text}")
        logger.info(f"原翻译: {translated_text}")
        logger.info(f"改进后的翻译: {improved_translation}")
        return improved_translation
    else:
        logger.info("原文与译文条数匹配，无需改进")
        return translated_text

def improve_translation_with_recommendation(
        llm: Any,
        chunk: Dict[str, Any], 
        translated_text: str,
        recommendation: str,
        system_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        log_fn: Callable[[str], None] = print) -> str:
    """根据改进意见改进翻译"""
    full_context = chunk['context']
    
    main_indices = chunk['main_indices']
    
    user_prompt = prompt.generate_improved_translation_prompt_with_recommendation(full_context,main_indices,translated_text,recommendation)
    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=max_tokens,
        temperature=temperature,

    )
    
    improved_translation = response["choices"][0]["message"]["content"].strip()
    
    # 删除<think>标签
    improved_translation = re.sub(r"<think>[\s\S]*?</think>", "", improved_translation)
    
    src_text = "\n".join([f"{i+1}. {s['text']}" for i, s in enumerate(chunk["main"])])
    
    log_fn(localization.get("msg_translated_text_improved"))
    logger.info(f"改进翻译提示词：{user_prompt}")
    logger.info(f"原文:{src_text}")
    logger.info(f"原翻译: {translated_text}")
    logger.info(f"改进后的翻译: {improved_translation}")
    return improved_translation