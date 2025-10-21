from typing import Dict, List, Callable, Any, Optional, Tuple
from service.translator import prompt
import re
from service.log import get_logger
from service import localization

logger = get_logger("LightVT")

def translate_text(
    llm: Any,
    text: str,
    system_prompt: str,
    max_tokens: int = 4096,
    temperature: float = 0.2,
    log_fn: Callable[[str], None] = print
) -> str:
    """使用LLM翻译纯文本"""
    
    text_length = len(text)
    log_fn(localization.get("msg_translating_text").format(characters_count=text_length))
    
    user_prompt = prompt.plain_text.generate_translation_prompt(text)
    
    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=max_tokens,
        temperature=temperature
    )
    
    translated_text = response["choices"][0]["message"]["content"].strip()
    
    log_fn(localization.get("msg_translation_complete")
        .format(result_length=len(translated_text)))
    logger.info(f"纯文本翻译结果：\n{translated_text}")
    
    return translated_text

def ask_for_recommendation(
        llm: Any,
        source_text:str,
        translated_text: str,
        target_lang: str, 
        max_tokens: int = 2048, 
        temperature: float = 0.1, 
        log_fn: Callable[[str], None] = print) -> str:
    """改进翻译结果"""
    
    review_system_prompt = prompt.plain_text.generate_recommendation_system_prompt(target_lang)
    user_prompt = prompt.plain_text.generate_recommendation_prompt(source_text, translated_text)
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

def improve_translation_with_recommendation(
        llm: Any,
        source_text: str, 
        translated_text: str,
        recommendation: str,
        system_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        log_fn: Callable[[str], None] = print) -> str:
    """根据改进意见改进翻译"""
    user_prompt = prompt.plain_text.generate_improved_translation_prompt_with_recommendation(source_text, translated_text, recommendation)
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
    
    log_fn(localization.get("msg_translated_text_improved"))
    logger.info(f"改进翻译提示词：{user_prompt}")
    logger.info(f"原文:{source_text}")
    logger.info(f"原翻译: {translated_text}")
    logger.info(f"改进后的翻译: {improved_translation}")
    return improved_translation