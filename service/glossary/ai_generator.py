# lightVT/service/glossary/ai_generator.py - 内部实现翻译函数

import json
import re
import math
import threading
from typing import Dict, List, Set, Tuple, Optional, Callable
from dataclasses import dataclass
from service import log,localization
from llama_cpp import Llama

logger = log.get_logger("AIGlossaryGenerator")
_progress_var = 0.0

@dataclass
class ExtractionConfig:
    """术语提取配置"""
    chunk_size: int = 200
    chunk_overlap: int = 50
    min_term_frequency: int = 2
    max_terms_per_chunk: int = 15
    min_term_length: int = 2
    max_term_length: int = 50

def _create_chat_completion(prompt: str,  llm: Llama) -> str:
    """🔥 内部翻译函数"""
    try:
        response = llm.create_chat_completion(
            messages=[
                {"role": "user", "content": prompt}
            ]
            ,
            temperature=0.1,
            max_tokens=4096,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"文本生成失败: {e}")
        raise e

def generate_glossary_from_subtitle(
    subtitle_text: str, 
    target_language: str,
    model_path: str,
    config: Optional[ExtractionConfig],
    stop_event: Optional[threading.Event],
    n_gpu_layers: int = -1,
    update_progress: Callable[[str, float], None] = None
) -> Dict[str, str]:
    """🔥 从字幕文本生成术语表 - 主函数（移除外部翻译函数参数）"""
    global _progress_var
    
    if not config:
        config = ExtractionConfig()
    
    logger.info("开始从字幕文本生成术语表")
    
    try:
        def add_progress(msg:str,increment: float):
            global _progress_var
            if update_progress:
                _progress_var += increment
                update_progress(msg, _progress_var)
                
        def set_progress(msg: str, value: float):
            global _progress_var
            if update_progress:
                _progress_var = value
                update_progress(msg, _progress_var)

        if stop_event.is_set():
            logger.info("生成术语表已被取消")
            return {}
        
        set_progress('', 0.0)

        # 步骤1: 预处理和切片
        cleaned_text = clean_subtitle_text(subtitle_text)
        chunks = split_text_into_chunks(cleaned_text, config)
        if not chunks:
            logger.warning("未提取到有效文本片段")
            return {}
        logger.info(f"文本已切分为 {len(chunks)} 个片段")
        add_progress(localization.get("log_glossary_text_split").format(count=len(chunks)), 0.1)

        if stop_event.is_set():
            logger.info("生成术语表已被取消")
            return {}
        
        llm = Llama(
            model_path=model_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=4096
        )
        # 步骤2: 从每个切片提取术语（包含上下文）
        term_contexts = extract_terms_with_context(chunks, llm, config, stop_event, add_progress)
        logger.info(f"提取到 {len(term_contexts)} 个带上下文的术语")
        logger.info(f"术语及上下文: {term_contexts}")
        
        # 步骤3: 统计术语频率
        term_frequencies = calculate_term_frequencies(term_contexts, cleaned_text)
        add_progress(localization.get("log_glossary_term_frequency_completed"), 0.05)
        logger.info(f"术语频率表：{term_frequencies}")

        # 步骤4: 过滤高频率术语
        high_freq_terms = filter_high_frequency_terms(term_frequencies, config)
        add_progress(localization.get("log_glossary_filter_terms").format(count=len(high_freq_terms)), 0.05)

        if not high_freq_terms:
            logger.warning("未提取到有效术语")
            return {}
        
        # 步骤5: 带上下文的术语翻译
        glossary = translate_terms_with_context(high_freq_terms, term_contexts, target_language, llm, stop_event, add_progress)

        logger.info(f"术语表生成完成，共 {len(glossary)} 个术语对")
        
        set_progress(localization.get('completed'), 1.0)
        
        return glossary
        
    except Exception as e:
        logger.error(f"生成术语表失败: {e}")
        return {}

def clean_subtitle_text(text: str) -> str:
    """清理字幕文本"""
    # 移除时间戳
    text = re.sub(r'\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}', '', text)
    
    # 移除序号行
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
    
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 移除字幕格式标记
    text = re.sub(r'\{[^}]*\}', '', text)  # 移除 {font} 等标记
    text = re.sub(r'\[[^\]]*\]', '', text)  # 移除 [music] 等标记
    
    # 统一换行和空格
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()

def split_text_into_chunks(text: str, config: ExtractionConfig) -> List[str]:
    """将文本切分为带重叠的片段 - 简化安全版"""
    if len(text) <= config.chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        # 计算片段结束位置
        end = min(start + config.chunk_size, len(text))
        
        # 在句子边界切分（限制回退范围）
        if end < len(text):
            # 只在后25%范围内寻找句子边界
            search_start = max(start + config.chunk_size * 3 // 4, start)
            for i in range(end, search_start, -1):
                if text[i] in '.!?。！？\n':
                    end = i + 1
                    break
        
        # 提取片段
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # 如果到达末尾，退出
        if end >= len(text):
            break
        
        # 计算下一个起始位置，确保前进
        start = max(start + 1, end - config.chunk_overlap)
    
    return chunks

def extract_terms_with_context(
    chunks: List[str], 
    llm: Llama,
    config: ExtractionConfig,
    stop_event: threading.Event,
    add_progress: Callable
) -> Dict[str, List[str]]:
    """🔥 从文本片段提取术语及其上下文（移除外部翻译函数参数）"""
    global _progress_var
    if chunks is None or len(chunks) == 0:
        logger.warning("没有可处理的文本片段")
        return {}
    
    term_contexts: Dict[str, List[str]] = {}  # 术语 -> 上下文列表
    
    progress_step = 0.5 / len(chunks)
    
    for i, chunk in enumerate(chunks):
        if stop_event.is_set():
            logger.info("术语提取已被取消")
            return {}
        
        logger.info(f"正在处理第 {i+1}/{len(chunks)} 个片段...")
        
        try:
            # 提取术语时保留上下文信息
            chunk_terms = extract_terms_from_chunk(chunk, config, i+1, llm)
            
            # 为每个术语记录上下文
            for term in chunk_terms:
                if term not in term_contexts:
                    term_contexts[term] = []
                
                # 提取术语的上下文（前后各50个字符）
                context = extract_term_context(chunk, term, context_window=80)
                if context and context not in term_contexts[term]:
                    term_contexts[term].append(context)
            
            logger.debug(f"提取到的术语: {chunk_terms}")

            add_progress(localization.get("log_glossary_chunk_complete").format(chunk_index=i+1, chunk_count=len(chunks), term_count=len(chunk_terms)), progress_step)

        except Exception as e:
            logger.error(f"处理片段 {i+1} 失败: {e}")
            continue
    
    return term_contexts

def extract_terms_from_chunk(
    chunk: str, 
    config: ExtractionConfig, 
    chunk_index: int,
    llm: Llama
) -> List[str]:
    """🔥 从单个文本片段提取术语（使用内部翻译函数）"""
    
    # 改进的提取提示，包含更多上下文指导
    prompt = f"""
请从以下文本中提取没有通用翻译标准的专有名词。

【提取标准】
1. **人名**
2. **绰号/昵称**
3. **具体地名**
4. **机构地名**

【避免提取】
- 常见动词、形容词、副词、介词、连词
- 一般性专业词汇（如：computer, internet, music, art, science等）
- 常见音乐术语
- 常见体育术语
- 基础学科词汇
- 有通用翻译标准的大众化的词汇

【质量要求】
- 术语长度在{config.min_term_length}-{config.max_term_length}个字符
- 最多提取{config.max_terms_per_chunk}个最重要的术语

【输出格式】
请以JSON数组格式输出：
["term1", "term2","term3", ...]

【文本内容】
{chunk}

请开始提取：
"""
    try:
        # 🔥 使用内部翻译函数
        response = _create_chat_completion(prompt, llm)
        terms = parse_term_extraction_response(response)
        return terms
        
    except Exception as e:
        logger.error(f"片段 {chunk_index} 术语提取失败: {e}")
        return []

def parse_term_extraction_response(response: str) -> List[str]:
    """解析术语提取响应"""
    try:
        # 提取JSON数组
        json_match = re.search(r'\[.*?\]', response, re.DOTALL)
        if json_match:
            json_text = json_match.group()
            terms_list = json.loads(json_text)
            
            if isinstance(terms_list, list):
                return [term.strip().lower() for term in terms_list if isinstance(term, str) and term.strip()]
        
        # 备用解析：逐行提取
        terms = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('"') and line.endswith('"'):
                term = line.strip('"').strip().lower()
                if 2 <= len(term) <= 50:
                    terms.append(term)
        
        return terms[:15]  # 限制数量
        
    except Exception as e:
        logger.error(f"解析术语提取响应失败: {e}")
        return []

def extract_term_context(text: str, term: str, context_window: int = 50) -> str:
    """提取术语的上下文"""
    try:
        # 查找术语位置（忽略大小写）
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        match = pattern.search(text)
        
        if not match:
            return ""
        
        start_pos = match.start()
        end_pos = match.end()
        
        # 提取前后上下文
        context_start = max(0, start_pos - context_window)
        context_end = min(len(text), end_pos + context_window)
        
        context = text[context_start:context_end].strip()
        
        # 在边界处截断到完整单词
        if context_start > 0:
            space_pos = context.find(' ')
            if space_pos > 0:
                context = context[space_pos+1:]
        
        if context_end < len(text):
            space_pos = context.rfind(' ')
            if space_pos > 0:
                context = context[:space_pos]
        
        return context
        
    except Exception:
        return ""

def calculate_term_frequencies(term_contexts: Dict[str, List[str]], cleaned_text: str) -> Dict[str, int]:
    """计算术语频率"""
    return {term: cleaned_text.lower().count(term) for term, contexts in term_contexts.items()}

def filter_high_frequency_terms(term_frequencies: Dict[str, int], config: ExtractionConfig) -> List[str]:
    """过滤高频率术语"""
    filtered_terms = []
    
    for term, frequency in term_frequencies.items():
        # 频率筛选
        if frequency < config.min_term_frequency:
            continue
        
        filtered_terms.append(term)
        # # # 质量筛选
        # if is_quality_term(term):
        #     filtered_terms.append(term)
    
    # 按频率排序，取前50个
    filtered_terms.sort(key=lambda x: term_frequencies[x], reverse=True)
    return filtered_terms[:50]

def is_quality_term(term: str) -> bool:
    """判断是否为高质量术语"""
    term = term.lower().strip()
    
    # 常见词汇黑名单
    common_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
        'after', 'above', 'below', 'between', 'among', 'around', 'over',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
        'can', 'must', 'shall', 'this', 'that', 'these', 'those', 'i', 'you',
        'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
        'my', 'your', 'his', 'her', 'its', 'our', 'their', 'very', 'so', 'too',
        'just', 'now', 'then', 'here', 'there', 'when', 'where', 'how', 'what',
        'who', 'which', 'why', 'if', 'because', 'since', 'until', 'while',
        'also', 'only', 'even', 'still', 'again', 'more', 'most', 'much',
        'many', 'some', 'any', 'all', 'both', 'each', 'every', 'other',
        'another', 'such', 'no', 'not', 'yes', 'get', 'make', 'take', 'come',
        'go', 'see', 'know', 'think', 'say', 'tell', 'feel', 'look', 'want',
        'use', 'find', 'give', 'work', 'call', 'try', 'ask', 'need', 'seem',
        'help', 'show', 'play', 'run', 'move', 'live', 'believe', 'hold',
        'bring', 'happen', 'write', 'provide', 'sit', 'stand', 'lose', 'pay'
    }
    
    if term in common_words:
        return False
    
    # 长度检查
    if len(term) <= 2 or len(term) > 50:
        return False
    
    # 纯数字或特殊字符
    if term.isdigit() or not re.search(r'[a-zA-Z]', term):
        return False
    
    # 专业术语特征检测
    professional_indicators = [
        r'[A-Z]{2,}',                    # 大写缩写 (API, CPU)
        r'\w+tion$',                     # -tion 结尾
        r'\w+ness$',                     # -ness 结尾
        r'\w+ment$',                     # -ment 结尾
        r'\w+ology$',                    # -ology 结尾
        r'\w+system$',                   # system 结尾
        r'\w+technology$',               # technology 结尾
        r'\w+analysis$',                 # analysis 结尾
        r'\w+method$',                   # method 结尾
        r'\w+algorithm$',                # algorithm 结尾
        r'\w+protocol$',                 # protocol 结尾
        r'\w+framework$',                # framework 结尾
        r'\w+interface$',                # interface 结尾
        r'\w+network$',                  # network 结尾
        r'\w+database$',                 # database 结尾
    ]
    
    for pattern in professional_indicators:
        if re.search(pattern, term, re.IGNORECASE):
            return True
    
    # 复合词检测
    if '-' in term or '_' in term:
        return True
    
    # 驼峰命名检测
    if len(re.findall(r'[A-Z]', term)) >= 2:
        return True
    
    # 默认：中等长度的词汇有可能是术语
    return 4 <= len(term) <= 20

def translate_terms_with_context(
    terms: List[str], 
    term_contexts: Dict[str, List[str]], 
    target_language: str,
    llm: Llama,
    stop_event: threading.Event,
    add_progress: Callable
) -> Dict[str, str]:
    """🔥 带上下文的术语翻译（使用内部翻译函数）"""
    global _progress_var
    glossary = {}
    batch_size = 10  
    progress_step = 0.3 / math.ceil(len(terms) / batch_size)
    batch_count = len(terms) // batch_size + 1
    
    for i in range(0, len(terms), batch_size):
        if stop_event.is_set():
            logger.info("术语翻译已被取消")
            return {}
        
        batch_terms = terms[i:i + batch_size]
        batch_index = i // batch_size + 1
        
        try:
           
            logger.info(f"正在翻译第 {batch_index} 批术语（{len(batch_terms)} 个）")

            # 构建带上下文的翻译提示
            prompt = build_context_aware_translation_prompt(
                batch_terms, term_contexts, target_language
            )
            
            # 🔥 使用内部翻译函数
            response = _create_chat_completion(prompt, llm)
            batch_glossary = parse_translation_response(response, batch_terms)
            
            # 去重：以第一次翻译为准
            for source, target in batch_glossary.items():
                if source not in glossary and target.strip():
                    glossary[source] = target.strip()

            add_progress(localization.get("log_glossary_batch_complete").format(batch_index=batch_index,batch_count=batch_count, chunk_count=batch_count), progress_step)

        except Exception as e:
            logger.error(f"第 {batch_index} 批术语翻译失败: {e}")
            continue
    
    return glossary

def build_context_aware_translation_prompt(
    terms: List[str], 
    term_contexts: Dict[str, List[str]], 
    target_language: str
) -> str:
    """构建带上下文的翻译提示"""
    
    terms_with_context = []
    
    for i, term in enumerate(terms):
        contexts = term_contexts.get(term, [])
        
        # 选择最有代表性的上下文
        best_context = ""
        if contexts:
            # 选择最长的上下文（通常包含更多信息）
            best_context = max(contexts, key=len)
            # 截断过长的上下文
            if len(best_context) > 150:
                best_context = best_context[:150] + "..."
        
        term_info = f"{i+1}. **{term}**"
        if best_context:
            term_info += f"\n   上下文: \"{best_context}\""
        
        terms_with_context.append(term_info)
    
    terms_text = "\n\n".join(terms_with_context)
    
    return f"""
请将以下术语准确翻译成{target_language}。每个术语都提供了上下文信息，请根据上下文确定最合适的翻译。

【翻译要求】
1. 根据上下文理解术语的具体含义和使用场景
2. 专业术语使用标准译名，保持行业一致性
3. 考虑术语在特定领域的专业含义
4. 专有名词可保留原文或使用通用译法
5. 避免过度解释，保持译文简洁准确

【注意事项】
- 同一术语在不同上下文中可能有不同翻译
- 优先使用该领域的标准译名
- 保持译文的专业性和可读性

【输出格式】
请严格按照JSON格式输出：
{{
  "artificial intelligence": "人工智能",
  "machine learning": "机器学习",
  "deep learning": "深度学习"
}}

【待翻译术语及上下文】
{terms_text}

请开始翻译：
"""

def parse_translation_response(response: str, original_terms: List[str]) -> Dict[str, str]:
    """解析翻译响应"""
    try:
        # 提取JSON部分
        json_match = re.search(r'\{.*?\}', response, re.DOTALL)
        if json_match:
            json_text = json_match.group()
            translations = json.loads(json_text)
            
            # 验证翻译结果
            valid_translations = {}
            original_terms_lower = [t.lower() for t in original_terms]
            
            for source, target in translations.items():
                source_clean = source.strip().lower()
                target_clean = str(target).strip()
                
                if source_clean in original_terms_lower and target_clean:
                    valid_translations[source_clean] = target_clean
            
            return valid_translations
        
        # 备用解析
        return fallback_parse_translation(response, original_terms)
        
    except Exception as e:
        logger.error(f"解析翻译响应失败: {e}")
        return fallback_parse_translation(response, original_terms)

def fallback_parse_translation(response: str, original_terms: List[str]) -> Dict[str, str]:
    """备用翻译解析"""
    translations = {}
    lines = response.split('\n')
    original_terms_lower = [t.lower() for t in original_terms]
    
    for line in lines:
        line = line.strip()
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                source = parts[0].strip().strip('"').lower()
                target = parts[1].strip().strip('"')
                
                if source in original_terms_lower and target:
                    translations[source] = target
    
    return translations