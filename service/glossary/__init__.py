# lightVT/service/glossary/__init__.py
"""
术语表管理模块
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from ..log import get_logger
from toolz import keyfilter, pipe
import utils
import threading
from service.glossary.ai_generator import generate_glossary_from_subtitle, ExtractionConfig

logger = get_logger("Glossary")
glossary: Dict[str, str] = {}

def load_glossary(filename: str):
    """加载术语表"""
    global glossary
    try:
        glossary_path = Path(f"cache/{filename}")
        if glossary_path.exists():
            with open(glossary_path, 'r', encoding='utf-8') as f:
                glossary = json.load(f)
                logger.info(f"已加载术语表，包含 {len(glossary)} 个术语")
        else:
            glossary = {}
            logger.info("未找到术语表文件，创建新的术语表")
    except Exception as e:
        logger.error(f"加载术语表失败: {e}")
        glossary = {}
        
def load_generated_glossary(subtitle_text: str, target_language: str, model_path: str, n_gpu_layers: int = -1, 
                                stop_event: threading.Event = None, update_progress=None):
    """从字幕文本加载生成的术语表"""
    global glossary
    try:
        generated_glossary = generate_from_subtitle_text(
            subtitle_text,
            target_language,
            model_path,
            n_gpu_layers=n_gpu_layers,
            stop_event=stop_event,
            update_progress=update_progress
        )
        glossary = generated_glossary
    except Exception as e:
        logger.error(f"生成术语表失败: {e}")

def save_glossary(filename:str):
    """保存术语表"""
    try:
        global glossary
        glossary_path = Path(f"cache/{filename}")
        # 确保目录存在
        glossary_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(glossary_path, 'w', encoding='utf-8') as f:
            json.dump(glossary, f, ensure_ascii=False, indent=2)
        logger.info(f"术语表已保存，包含 {len(glossary)} 个术语")
    except Exception as e:
        logger.error(f"保存术语表失败: {e}")

def add_term(source_term: str, target_term: str):
    """添加术语"""
    global glossary
    glossary[source_term.strip()] = target_term.strip()

def remove_term(source_term: str):
    """删除术语"""
    global glossary
    if source_term in glossary:
        del glossary[source_term]

def get_terms() -> Dict[str, str]:
    """获取所有术语"""
    global glossary
    return glossary.copy()

def clear_glossary():
    """清空术语表"""
    global glossary
    glossary.clear()

def apply_glossary_to_text( text: str) -> str:
    """将术语表应用到文本中"""
    global glossary
    if not glossary:
        return text
    
    # 按术语长度排序，优先替换长术语
    sorted_terms = sorted(glossary.items(), key=lambda x: len(x[0]), reverse=True)

    result = text
    for source_term, target_term in sorted_terms:
        # 使用正则表达式进行精确匹配，避免部分匹配
        pattern = r'\b' + re.escape(source_term) + r'\b'
        result = re.sub(pattern, target_term, result, flags=re.IGNORECASE)
    
    return result

def generate_glossary_prompt(source_text:str) -> str:
    """生成包含术语表的提示词"""
    global glossary
    if not glossary:
        return ""
    
    source_glossary = keyfilter(lambda k: k in source_text.lower(), glossary)
    
    if not source_glossary or len(source_glossary) == 0:
        return ""

    terms_text = "\n".join([f"- {source} → {target}" for source, target in source_glossary.items()])

    return f"""
【术语表】
{terms_text}
"""

def is_empty() -> bool:
    """检查术语表是否为空"""
    global glossary
    return len(glossary) == 0

def generate_from_subtitle_text(subtitle_text: str, target_language: str, model_path: str, n_gpu_layers: int = -1, 
                                stop_event: threading.Event = None, update_progress=None) -> Dict[str, str]:
    """从字幕文本智能生成术语表"""
    try:
        # 简化调用，不需要传入翻译函数
        config = ExtractionConfig(
            chunk_size=1000,          # 每片段2000字符
            min_term_frequency=2,     # 最少出现2次
            max_terms_per_chunk=15,   # 每片段最多15个术语
            min_term_length=3,        # 最小长度3个字符
            max_term_length=50        # 最大长度50个字符
        )
        
        # 直接调用，内部处理翻译
        generated_glossary = generate_glossary_from_subtitle(
            subtitle_text, 
            target_language, 
            model_path,
            config=config,
            stop_event=stop_event,
            n_gpu_layers=n_gpu_layers,
            update_progress=update_progress
        )
        
        logger.info(f"从字幕文本生成术语表完成，共 {len(generated_glossary)} 个术语")
        return generated_glossary
        
    except Exception as e:
        logger.error(f"从字幕文本生成术语表失败: {e}")
        return {}
    
def to_glossary_filename(file_path:str) -> str:
    """将文件路径转换为术语表文件名"""
    return pipe(file_path,
                utils.get_filename, 
                utils.string_to_base64)