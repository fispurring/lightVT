from typing import Dict, List, Callable, Any, Optional, Tuple, Any
from service import localization
from service import glossary

def generate_system_prompt(source_lang: str, target_lang: str) -> str:
    """生成系统提示"""
    translate_lang = None
    
    lang_to_iso = localization.get("lang_to_iso")
    if lang_to_iso[source_lang] == "auto":
        translate_lang = f"请自动检测输入字幕语言，并将其翻译成{target_lang}。"
    else:
        translate_lang = f"请将原字幕从{source_lang}翻译成{target_lang}。"
    
    return f"""你是一个专业的字幕翻译专家。{translate_lang}。

重要规则：
1. 只输出翻译后的文本，不要有任何解释、注释或标记
2. 保持原文的格式和语气，确保翻译自然流畅
3. 如果遇到歌词，请直接翻译，不要用星号或其他符号替代
4. 保持歌词的音乐符号 ♪
5. 每个条目都以序号开头，一个条目可能有多行，不应该将一个条目的多行视为多条字幕
6. 你可以进行深度思考，但不要在输出中包含任何 `<think>` `</think>` 标签或其内容。

比如：
[[1]]
I could often read by means
of the tenure of her speech
尽管有2行，但应被视为1条字幕


示例1：

    原文: 
    [[1]]
    ♪ Hello world ♪

    译文: 
    [[1]]
    ♪ 你好世界 ♪

示例2：
    原文:
    [[1]]
    I could often read by means
    of the tenure of her speech
    [[2]]
    or certain facial expressions,
    [[3]]
    the emotional import
    of what she was saying.
    [[4]]
    And she was often vexed with me.

    错误译文（擅自合并条目）：
    [[1]]
    我常常可以通过她说话的方式
    或某些面部表情
    [[2]]
    来了解她说的话中的情感  
    [[3]]
    并且她经常对我感到不满 

    正确译文：
    [[1]]
    我常常可以通过她说话的方式
    [[2]]
    或某些面部表情
    [[3]]
    来了解她说的话中的情感  
    [[4]]
    并且她经常对我感到不满

示例3：
    原文:
    [[1]]
    But if you see that I'm done for,
    [[2]]
    well, you're gonna have to do
    for yourself.
    [[3]]
    Now you put it right there
    so's you can't miss.

    错误译文（第8条是一条包含了2行的字幕，不是2条字幕）: 
    [[1]]
    但如果你看到我完了，
    [[2]]
    那么，你就得自己了结自己。
    [[3]]
    现在你把它放在那里，
    [[4]]
    这样你就不会打不中。 

    正确译文: 
    [[1]]
    但如果你看到我完了，
    [[2]]
    那么，你就得自己了结自己。
    [[3]]
    现在你把它放在那里，
    这样你就不会打不中。 
"""

def generate_recommendation_system_prompt(target_lang: str) -> str:
        return f"""你是专业的翻译质量评估专家。
任务：评估字幕翻译质量，仅在发现严重问题时给出改进建议。自动检测原文语言，译文目标语言是{target_lang}。
原则：
    检查译文语言是否为{target_lang}，如果不是，请给出建议。
    好的翻译不需要强行改进。
"""

# def generate_translation_prompt(context_chunk: List[Dict], main_indices: List[int]) -> str:
#     """生成包含上下文的翻译提示"""
    
#     # 构建上下文文本
#     context_text = "\n".join([f"{i+1}. {s['text']}" for i, s in enumerate(context_chunk)])
    
#     main_text = "\n".join([f"{i+1}. {context_chunk[i]['text']}" for i in main_indices])
    
#     # 标记需要翻译的部分
#     translate_indices = [str(i+1) for i in main_indices]
    
#     return f"""请翻译以下字幕，注意保持上下文连贯性。

# 原文上下文：
# {context_text}

# 只翻译序号为 {', '.join(translate_indices)} 的字幕，其他字幕只作为上下文环境参考，绝对不要翻译
# 保持人称代词、术语翻译的一致性。

# 翻译结果格式：
# 编号. 翻译内容"""

def parse_chunk(chunk: List[Dict]) -> str:
    """将字幕块转换为字符串"""
    return "\n".join([f"[[{s['id']}]]\n{s['text']}" for i, s in enumerate(chunk)])

def generate_translation_prompt(context_chunk: List[Dict], main_indices: List[int]) -> str:
    """生成翻译提示 - 分离上下文和目标内容"""
    
    # 分离上下文和目标翻译内容
    context_lines = []  # 仅参考的上下文
    target_lines = []   # 需要翻译的内容
    
    for i, s in enumerate(context_chunk):
        if i in main_indices:
            # 需要翻译的内容
            target_lines.append(s)
        else:
            # 仅作为上下文参考
            context_lines.append(s)
            
    # 构建上下文文本
    context_text = parse_chunk([v for i,v in enumerate(context_chunk) if i not in main_indices])
    
    target_text = parse_chunk([context_chunk[i] for i in main_indices])

    
    # 构建目标翻译文本
    target_text = parse_chunk(target_lines)
    
    # 计算信息
    expected_count = len(main_indices)
    start_num = context_chunk[main_indices[0]]['id']
    end_num = context_chunk[main_indices[-1]]['id']
    
    # 术语表
    glossary_prompt = glossary.generate_glossary_prompt()
    
    return f"""/nothink
请翻译指定的字幕内容。

【上下文参考】（仅供理解语境，不要翻译）：
{context_text}

【翻译目标】（编号{start_num}-{end_num}，共{expected_count}条）：
{target_text}

{glossary_prompt}

【思维步骤】
1. 阅读上下文，理解整体语境和情感色彩，但不要翻译这部分内容
2. 分析翻译目标，理清一共有多少条字幕（一个编号及编号下面的内容算一条）
3. 执行翻译，确保翻译出来的字幕数量和编号与翻译目标一致，术语表中的术语请严格按照对应关系翻译
4. 检查每个条目的编号和内容，确保编号和内容之间有换行，确保没有遗漏或合并条目

【重要指令】
1. 只翻译"翻译目标"部分的{expected_count}条内容
2. "上下文参考"仅用于理解语境，绝对不要翻译
3. 保持原有编号{start_num}到{end_num}
4. 歌词部分请直接翻译，不要用星号或其他符号替代
5. 保持人称代词、术语翻译的一致性
6. 格式：
[[编号]]
翻译内容

编号与翻译内容之间一定要换行

请开始翻译："""

def generate_recommendation_prompt(context_chunk: List[Dict], main_indices: List[int],translated_text:str):
    """生成改进建议提示"""
    
    # 构建上下文文本
    context_text = parse_chunk([v for i,v in enumerate(context_chunk) if i not in main_indices])
    
    main_text = parse_chunk([context_chunk[i] for i in main_indices])
    
    # 标记需要翻译的部分
    translate_indices = [str(i+1) for i in main_indices]
    
    return f"""请查阅原文以及译文，检查译文是否已经翻译，评估翻译质量，提出简洁明了的改进建议。

上下文参考（仅供理解语境，不是要翻译的原文）：
{context_text}

原文：
{main_text}

译文：
{translated_text}

只在发现明显错误时给建议：
- 误译、漏译
- 语法错误
- 表达不自然
- 词句未翻译
"""

def generate_review_translation_prompt(context_chunk: List[Dict], main_indices: List[int],translated_text:str) -> str:
    """生成包含上下文的翻译提示"""
    
    main_text = parse_chunk([context_chunk[i] for i in main_indices])
    
    # 计算需要输出的字幕条数
    expected_count = len(main_indices)
    
    return f"""/nothink
译文与原文的序号内容不匹配，请重新翻译原文 ，新译文严格保持与原文序号内容一致。

原文：
{main_text}

错误译文：
{translated_text}

【思维步骤】
1. 检查原文与错误译文的每一条字幕，找出翻译不匹配的条目
2. 重新翻译原文，确保新译文每条字幕的编号和内容与原文严格对应

【重要】格式要求：
1. 必须输出 {expected_count} 条字幕
2. 绝对不能丢失、合并或跳过任何条目
3. 只给出译文，不要有任何解释、注释或标记

翻译结果格式：
[[编号]]
翻译内容

编号与翻译内容之间一定要换行

示例1：
    原文:
    [[432]]
    shall not perish
    [[433]]
    from the earth.
    [[434]]
    [applause]
    
    错误译文：
    [[432]]
    不会从大地上消失
    [[433]]
    [[434]]
    [掌声]
    
    新译文：
    [[432]]
    不会从
    [[433]]
    大地上消失
    [[434]]
    [掌声]
    
示例2：
    原文:
    [[432]]
    shall not perish
    [[433]]
    from the earth.
    [[434]]
    [applause]
    
    错误译文：
    [[432]]
    不会从大地上消失
    [[433]]
    [掌声]
    
    新译文：
    [[432]]
    不会从
    [[433]]
    大地上消失
    [[434]]
    [掌声]
"""

def generate_improved_translation_prompt_with_recommendation(context_chunk: List[Dict], main_indices: List[int],translated_text:str,recommendation:str) -> str:
    """生成包含上下文的翻译提示"""
    
    # 构建上下文文本，明确标记翻译目标
    context_text = parse_chunk([v for i,v in enumerate(context_chunk) if i not in main_indices])
    
    main_text = parse_chunk([context_chunk[i] for i in main_indices])
    
    # 标记需要翻译的部分
    translate_indices = [str(i+1) for i in main_indices]
    
    # 计算需要输出的字幕条数
    expected_count = len(main_indices)
    
    return f"""/nothink
请根据建议改进翻译，严格保持字幕条数不变。

上下文参考（仅供理解语境，不是要翻译的原文）：
{context_text}

原文：
{main_text}

译文：
{translated_text}

改进建议:
{recommendation}

结合原文、译文以及改进建议，输出最终的翻译译文。
只翻译原文，上下文只作为参考，绝对不要翻译
保持人称代词、术语翻译的一致性。

【重要】格式要求：
1. 必须输出 {expected_count} 条字幕
2. 绝对不能丢失、合并或跳过任何条目
3. 歌词部分请直接翻译，不要用星号或其他符号替代
4. 只给出译文，不要有任何解释、注释或标记

翻译结果格式：
[[编号]]
翻译内容

编号与翻译内容之间一定要换行
"""