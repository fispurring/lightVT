from typing import Dict, List, Callable, Any, Optional, Tuple, Any
from service import localization
from service import glossary

def generate_system_prompt(source_lang: str, target_lang: str) -> str:
    """生成纯文本翻译系统提示"""
    translate_lang = None
    
    lang_to_iso = localization.get("lang_to_iso")
    if lang_to_iso[source_lang] == "auto":
        translate_lang = f"请自动检测输入文本语言，并将其翻译成{target_lang}。"
    else:
        translate_lang = f"请将原文本从{source_lang}翻译成{target_lang}。"
    
    return f"""你是一个专业的文本翻译专家。{translate_lang}。
重要规则：
1. 只输出翻译后的文本，不要有任何解释、注释或标记
2. 保持原文的格式和语气，确保翻译自然流畅
3. 如果遇到歌词，请直接翻译，不要用星号或其他符号替代
4. 保持歌词的音乐符号 ♪
5. 你可以进行深度思考，但不要在输出中包含任何 `<think>` `</think>` 标签或其内容。
"""

def generate_translation_prompt(text: str) -> str:
    """生成纯文本翻译提示"""
    return f"""请翻译以下文本：

{text}

"""