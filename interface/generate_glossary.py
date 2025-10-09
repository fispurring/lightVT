from service.extractor import extract_subtitles_to_file
from service.extractor import extract_subtitles
from service.translator import translate_srt_file
from service.translator import translate_srt_text
from defs import FileType, get_supported_subtitle_types, get_supported_video_types
from service import localization
from service import glossary
import utils
    
def generate_glossary(args):
    """生成术语表"""
    input_file = args['input']
    model_path = args.get('model_path')
    target_lang = args.get('target_lang', '简体中文')
    n_gpu_layers = args.get('n_gpu_layers', -1)
    stop_event = args.get('stop_event')
    update_progress = args.get('update_progress', None)
    processing_mode = args.get('processing_mode', 'translate')

    if not input_file:
        update_progress(localization.get('error_input_file_empty'), 0)
        return

    if not model_path:
        update_progress(localization.get('error_model_path_empty'), 0)
        return
    
    if not processing_mode:
        update_progress(localization.get('error_processing_mode_empty'), 0)
        return
    
    if processing_mode == 'translate_plain_text':
        # 处理纯文本文件
        subtitles_text = utils.safe_read_file(input_file)
        update_progress(localization.get('log_translating_plain_text'), 0)
        return glossary.generate_from_subtitle_text(subtitles_text, 
                                                    target_lang, 
                                                    model_path=model_path,
                                                    n_gpu_layers=n_gpu_layers, 
                                                    stop_event=stop_event, 
                                                    update_progress=update_progress)
    
    if input_file.endswith('.srt'):
        # 如果是SRT文件，直接使用现有的生成逻辑
        subtitles_text = utils.safe_read_file(input_file)

        return glossary.generate_from_subtitle_text(subtitles_text, 
                                                    target_lang, 
                                                    model_path=model_path,
                                                    n_gpu_layers=n_gpu_layers, 
                                                    stop_event=stop_event, 
                                                    update_progress=update_progress)
    else:
        # 如果是视频文件，先提取字幕再生成术语表
        subtitles_text = extract_subtitles(input_file)
        # 使用现有的生成逻辑
        return glossary.generate_from_subtitle_text(subtitles_text, 
                                                    target_lang, 
                                                    model_path=model_path,
                                                    n_gpu_layers=n_gpu_layers, 
                                                    stop_event=stop_event,
                                                    update_progress=update_progress)