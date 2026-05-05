# utils/llm_utils.py - 通用 LLM 响应处理工具

import logging
import re
from typing import List

logger = logging.getLogger(__name__)


def strip_thinking(response: str) -> str:
    """剥除 LLM 思考过程（Reasoning/Thinking 标签及内容），保留最终答案。

    针对 Qwen / DeepSeek-R1 等模型输出超长思考过程且无明确终止标记的情况，
    采用多级强制策略：
    1. 移除所有已知思考标签（<think>, <thinking>, <reasoning>, <thought>）
    2. 若文本以思考段落开头，强制截断到第一个 JSON 标记（[ 或 {）
    3. 若不含 JSON 标记但明显是思考过程，返回空字符串
    """
    if not response:
        return ""

    # 1. 移除各种思考标签（支持多行，大小写不敏感）
    for tag in ['think', 'thinking', 'reasoning', 'thought']:
        response = re.sub(
            rf'<{tag}>.*?</{tag}>',
            '', response, flags=re.DOTALL | re.IGNORECASE
        )

    # 2. 尝试基于终止标记的精确剥离（DeepSeek / Qwen 部分情况）
    response = re.sub(
        r'(?:Thinking\s*Process|Reasoning|思考过程|分析过程)[:：]\s*.*?'
        r'(?:Output[:：]|Final\s*Answer[:：]|答案[:：]|请开始提取：|请输出|JSON\s*输出|输出格式[:：])\s*',
        '',
        response,
        flags=re.DOTALL | re.IGNORECASE
    )

    # 3. 核心修复：若响应开头明显是思考过程（无论是否有终止标记），强制截断到第一个 JSON 标记
    thinking_indicators = [
        r'^\s*\d+\.\s*\*\*Analyze.*\*\*',       # 1. **Analyze...**
        r'^\s*\d+\.\s*Analyze',                    # 1. Analyze
        r'^\s*\*\*Thinking\s*Process\*\*',        # **Thinking Process**
        r'^\s*Thinking\s*Process[:：]',            # Thinking Process:
        r'^\s*Reasoning[:：]',                     # Reasoning:
        r'^\s*Step\s*\d+[:：\.]',                  # Step 1:
        r'^\s*Task[:：]',                          # Task:
        r'^\s*Categories[:：]',                    # Categories:
        r'^\s*\d+\.\s*(?:Analyze|Task|Step|Categories|Avoid|Quality|Output)',  # 编号列表项
    ]

    # 找到第一个 JSON 标记的位置
    first_json = -1
    for marker in ['[', '{']:
        pos = response.find(marker)
        if pos != -1 and (first_json == -1 or pos < first_json):
            first_json = pos

    # 如果开头匹配思考过程特征，强制截断到第一个 JSON 标记之前的内容
    prefix = response[:first_json] if first_json != -1 else response
    is_thinking_start = any(
        re.search(pattern, prefix, re.IGNORECASE | re.MULTILINE)
        for pattern in thinking_indicators
    )

    if is_thinking_start and first_json != -1:
        logger.debug(f"检测到思考过程前缀（{len(prefix)} 字符），强制截断到第一个 JSON 标记")
        response = response[first_json:]
    elif is_thinking_start and first_json == -1:
        # 明显是思考过程但不含任何 JSON 标记，安全丢弃
        logger.debug("响应仅为思考过程，不含 JSON 标记，返回空字符串")
        return ""

    # 4. 二次兜底：若截断后仍残留思考特征（如末尾的分析总结），清理常见污染
    response = re.sub(
        r'\n\s*(?:Note[:：]|注意[:：]|Reminder[:：]|提醒[:：]).*$',
        '', response, flags=re.DOTALL | re.IGNORECASE
    )

    return response.strip()


def extract_quoted_strings(response: str) -> List[str]:
    """从任意文本中提取双引号包围的字符串"""
    terms = []
    seen = set()
    for match in re.finditer(r'"([^"\n]{2,50})"', response):
        term = match.group(1).strip().lower()
        if term and term not in seen:
            seen.add(term)
            terms.append(term)
    return terms[:15]


def extract_markdown_list_terms(response: str) -> List[str]:
    """从 markdown 列表项中提取术语"""
    terms = []
    seen = set()
    patterns = [
        r'(?:^|\n)\s*[-*]\s*"?([^"\n]{2,50})"?\s*$',
        r'(?:^|\n)\s*\d+\.\s*"?([^"\n]{2,50})"?\s*$',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, response, re.MULTILINE):
            term = match.group(1).strip().strip('"').strip("'").lower()
            if 2 <= len(term) <= 50 and re.search(r'[a-zA-Z]', term) and term not in seen:
                seen.add(term)
                terms.append(term)
    return terms[:15]
