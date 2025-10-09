from enum import Enum

class FileType(Enum):
    VIDEO = "video"
    SUBTITLE = "subtitle"
    
def get_supported_text_types():
    """
    获取支持的纯文本文件扩展名列表
    """
    return (".txt", "*.*")
    
def get_supported_subtitle_types():
    """
    获取支持的字幕文件扩展名列表
    """
    return (".srt",)

def get_supported_video_types():
    """
    获取支持的视频文件扩展名列表
    """
    return (".mp4", ".avi", ".mkv", ".mov", ".flv", ".wmv")