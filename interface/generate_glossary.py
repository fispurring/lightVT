from service.extractor import extract_subtitles_to_file
from service.extractor import extract_subtitles
from service.translator import translate_srt_file
from service.translator import translate_srt_text
from defs import FileType, get_supported_subtitle_types, get_supported_video_types
from service import localization
from service import glossary
    
def generate_glossary(args):
    """生成术语表"""
    input_file = args['input']
    model_path = args.get('model_path')
    target_lang = args.get('target_lang', '简体中文')
    n_gpu_layers = args.get('n_gpu_layers', -1)
    if input_file.endswith('.srt'):
        # 如果是SRT文件，直接使用现有的生成逻辑
        with open(input_file, 'r', encoding='utf-8') as f:
            subtitles_text = f.read()

        return glossary.generate_from_subtitle_text(subtitles_text, target_lang, model_path=model_path,n_gpu_layers=n_gpu_layers)
    else:
        # 如果是视频文件，先提取字幕再生成术语表
        subtitles_text = extract_subtitles(input_file)
        # 使用现有的生成逻辑
        return glossary.generate_from_subtitle_text(subtitles_text, target_lang, model_path=model_path,n_gpu_layers=n_gpu_layers)