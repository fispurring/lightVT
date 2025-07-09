from service.extractor import extract_subtitles_to_file
from service.extractor import extract_subtitles
from service.translator import translate_srt_file
from service.translator import translate_srt_text
from defs import FileType, get_supported_subtitle_types, get_supported_video_types
from service import localization

def get_file_type(file_path):
    """
    根据文件路径获取文件类型
    file_path: 文件路径字符串
    返回: FileType 枚举值
    """
    if file_path.lower().endswith(get_supported_subtitle_types()):
        return FileType.SUBTITLE
    elif file_path.endswith(get_supported_video_types()):
        return FileType.VIDEO
    else:
        raise ValueError("不支持的文件类型")

def process_video_file(args):
    """
    处理视频文件的主函数
    args: 包含所有参数的字典
    """
    # 您的原始处理逻辑
    input_file = args['input']
    output_file = args['output']
    model_path = args.get('model_path')
    source_lang = args.get('source_lang', '英语')
    target_lang = args.get('target_lang', '简体中文')
    extract_only = args.get('extract_only', False)
    translate_only = True if get_file_type(input_file) == FileType.SUBTITLE else False
    gpu_layers = args.get('gpu_layers', 0)
    stop_event = args.get('stop_event')
    log_callback = args.get('log_callback', print)
    reflection_enabled = args.get('reflection_enabled', False)
    
    try:
        # 检查停止事件
        if stop_event and stop_event.is_set():
            return False
            
        start_processing = localization.get("start_processing")
        log_callback(f"{start_processing}...")
        
        # 您的具体处理逻辑在这里
        # 例如：
        # 1. 提取字幕
        # 2. 翻译字幕
        # 3. 保存结果
        
        # 示例处理逻辑
        if extract_only:
            log_extracting_subtitles = localization.get("log_extracting_subtitles")
            log_callback(log_extracting_subtitles)
            extract_subtitles_to_file(input_file, output_file)
        elif translate_only:
            log_translating_subtitles = localization.get("log_translating_subtitles")
            log_callback(log_translating_subtitles)
            
            translate_srt_file(
                input_path=input_file,
                output_path=output_file,
                model_path=model_path,
                source_lang=source_lang,
                target_lang=target_lang,
                n_gpu_layers=gpu_layers,
                reflection_enabled=reflection_enabled,
                log_fn=log_callback,
                stop_event=stop_event
            )
            # translate_subtitles(input_file, output_file, model_path)
        else:
            log_extracting_and_translating_subtitles = localization.get("log_extracting_and_translating_subtitles")
            log_callback(log_extracting_and_translating_subtitles)
            subtitles_text=extract_subtitles(input_file)
            translate_srt_text(
                input_text=subtitles_text,
                output_path=output_file,
                model_path=model_path,
                source_lang=source_lang,
                target_lang=target_lang,
                n_gpu_layers=gpu_layers,
                reflection_enabled=reflection_enabled,
                log_fn=log_callback,
                stop_event=stop_event
            )
        
        return True
        
    except Exception as e:
        log_callback(f"处理出错: {str(e)}")
        raise