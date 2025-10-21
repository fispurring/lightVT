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
    # 术语表
    glossary_prompt = glossary.generate_glossary_prompt(text)
    return f"""请翻译以下文本：
{text}

{glossary_prompt}

"""

def generate_recommendation_system_prompt(target_lang: str) -> str:
        return f"""你是专业的翻译质量评估专家。
任务：评估文本翻译质量，仅在发现严重问题时给出改进建议。自动检测原文语言，译文目标语言是{target_lang}。
原则：
    检查译文语言是否为{target_lang}，如果不是，请给出建议。
    好的翻译不需要强行改进。
"""

def generate_recommendation_prompt(source_text:str,translated_text:str):
    """生成改进建议提示"""
    
    return f"""请查阅原文以及译文，评估翻译质量，提出简洁明了的改进建议。

原文：
{source_text}

译文：
{translated_text}

"""

def generate_improved_translation_prompt_with_recommendation(source_text: str, translated_text:str,recommendation:str) -> str:
    """生成包含上下文的翻译提示"""
    # 计算需要输出的字幕条数
    return f"""/nothink
请根据建议改进翻译。

原文：
{source_text}

译文：
{translated_text}

改进建议:
{recommendation}

结合原文、译文以及改进建议，输出最终的翻译译文。
保持人称代词、术语翻译的一致性。

【重要】格式要求：
1. 只给出译文，不要有任何解释、注释或标记
"""