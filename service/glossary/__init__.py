# lightVT/service/glossary/__init__.py
"""
术语表管理模块
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from ..log import get_logger

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

def generate_glossary_prompt() -> str:
    """生成包含术语表的提示词"""
    global glossary
    if not glossary:
        return ""

    terms_text = "\n".join([f"- {source} → {target}" for source, target in glossary.items()])

    return f"""
【术语表】
{terms_text}
"""