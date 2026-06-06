# utils/grammars.py - GBNF Grammar 常量，强制 LLM 输出结构化 JSON

import json
import logging
from typing import Dict, List, Any
from .llm_utils import strip_thinking, strip_thinking_tags

logger = logging.getLogger(__name__)

# ── JSON 字符串数组 Grammar ──────────────────────────────────────────
# 输出格式: ["item1", "item2", "item3"]
#
# 用于:
#   - 术语表提取 (extract_terms_from_chunk)
#   - 字幕翻译 (translate_text / improve / review)
#
JSON_STRING_ARRAY = r"""
root ::= arr
arr  ::= "[" ws (string (ws "," ws string)*)? ws "]"
string ::= "\"" char* "\""
char ::= [^"\\\n] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])
ws ::= [ \n\t]*
"""

# ── JSON 字符串对象 Grammar ──────────────────────────────────────────
# 输出格式: {"term1": "translation1", "term2": "translation2"}
#
# 用于:
#   - 术语翻译 (translate_terms_with_context)
#
JSON_STRING_OBJECT = r"""
root ::= object
object ::= "{" ws (pair (ws "," ws pair)*)? ws "}"
pair ::= string ws ":" ws string
string ::= "\"" char* "\""
char ::= [^"\\\n] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])
ws ::= [ \n\t]*
"""


# ── JSON 数组 → 字幕 [[N]] 格式转换 ──────────────────────────────────

def _decode_json_string_array(json_str: str) -> List[str]:
    """从模型输出中恢复第一个 JSON 字符串数组。"""
    decoder = json.JSONDecoder()
    original = json_str.strip()
    cleaned = strip_thinking(json_str).strip()

    sources = [original, cleaned] if original.startswith("[") else [cleaned, original]
    candidates = []
    for source in sources:
        if source not in candidates:
            candidates.append(source)
        candidates.extend(source[index:] for index, char in enumerate(source) if char == "[")

    for candidate in candidates:
        if not candidate:
            continue
        try:
            value, _ = decoder.raw_decode(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return value

    return []


def json_array_to_subtitle_format(
    json_str: str,
    full_context: List[Dict[str, Any]],
    main_indices: List[int]
) -> str:
    """将 JSON 字符串数组转换为 [[N]] 格式的字幕文本。

    Args:
        json_str:   LLM 输出的 JSON 字符串数组，如 '["译1","译2\\n多行"]'
        full_context: 完整的上下文字幕列表
        main_indices: 需要翻译的字幕在 full_context 中的索引

    Returns:
        [[N]] 格式的字幕文本，如果 JSON 无法恢复则返回空字符串
    """
    translations = _decode_json_string_array(json_str)
    if not translations:
        logger.warning("未能从 LLM 输出恢复 JSON 字符串数组，返回空翻译")
        return ""

    result = []
    for i, translation in enumerate(translations):
        if i >= len(main_indices):
            break
        subtitle_id = full_context[main_indices[i]]['id']
        cleaned_translation = strip_thinking_tags(translation)
        result.append(f"[[{subtitle_id}]]")
        result.append(cleaned_translation)

    if not result:
        logger.warning("JSON 数组为空，返回空翻译")
        return ""

    return "\n".join(result)
