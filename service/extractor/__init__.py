import ffmpeg
import os
import uuid

def extract_subtitles(input_file):
    """
    从视频文件中提取字幕流并返回字幕内容作为字符串。
    在 cache 目录中生成临时文件，使用完后自动删除。
    
    :param input_file: 输入视频文件路径
    :return: 字幕内容字符串，如果没有字幕流则返回空字符串
    """
    # 创建 cache 目录
    cache_dir = os.path.join(os.getcwd(), "cache")
    os.makedirs(cache_dir, exist_ok=True)  # 确保目录存在

    # 生成唯一的临时文件名
    temp_file_path = os.path.join(cache_dir, f"{uuid.uuid4()}.srt")

    try:
        # 获取视频信息
        probe = ffmpeg.probe(input_file)
        
        # 查找字幕流
        subtitle_stream = next(
            (stream for stream in probe['streams'] if stream['codec_type'] == 'subtitle'),
            None
        )
        
        if subtitle_stream:
            # 提取字幕到临时文件
            stream = ffmpeg.input(input_file)
            stream = ffmpeg.output(stream, temp_file_path, 
                                map=f"0:{subtitle_stream['index']}", 
                                c='srt')
            ffmpeg.run(stream, overwrite_output=True)
            
            # 读取临时文件内容
            with open(temp_file_path, 'r', encoding='utf-8') as f:
                subtitles = f.read()
            
            # 删除临时文件
            os.remove(temp_file_path)
            
            return subtitles
        else:
            print("视频不包含字幕流")
            return ""
    
    except ffmpeg.Error as e:
        print(f"错误: {e.stderr.decode()}")
        # 删除临时文件（如果存在）
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return ""

def extract_subtitles_to_file(input_file, output_file):
    try:
        # 获取视频信息
        probe = ffmpeg.probe(input_file)
        
        # 查找字幕流
        subtitle_stream = next(
            (stream for stream in probe['streams'] if stream['codec_type'] == 'subtitle'),
            None
        )
        
        if subtitle_stream:
            # 提取字幕
            stream = ffmpeg.input(input_file)
            stream = ffmpeg.output(stream, output_file, 
                                  map=f"0:{subtitle_stream['index']}", 
                                  c='srt')
            ffmpeg.run(stream, overwrite_output=True)
            return True
        else:
            print("视频不包含字幕流")
            return False
            
    except ffmpeg.Error as e:
        print(f"错误: {e.stderr.decode()}")
        return False