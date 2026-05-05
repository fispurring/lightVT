# utils/grammars.py - GBNF Grammar 常量，强制 LLM 输出结构化 JSON

import json
import logging
from typing import Dict, List, Any

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
        [[N]] 格式的字幕文本，如果 JSON 解析失败则返回 strip 后的原文
    """
    try:
        translations = json.loads(json_str)
        if not isinstance(translations, list):
            logger.warning("JSON 解析成功但结果不是数组，回退")
            return json_str
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"JSON 解析失败: {e}，回退原始输出")
        return json_str

    result = []
    for i, translation in enumerate(translations):
        if i >= len(main_indices):
            break
        subtitle_id = full_context[main_indices[i]]['id']
        result.append(f"[[{subtitle_id}]]")
        result.append(str(translation))

    if not result:
        logger.warning("JSON 数组为空，回退")
        return json_str

    return "\n".join(result)
