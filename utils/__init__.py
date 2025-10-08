import sys
import os
from pathlib import Path
import pynvml
import base64
from defs import FileType, get_supported_subtitle_types, get_supported_video_types
import chardet
from . import settings

def get_gpu_info():
    """获取GPU信息"""
    try:
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        
        if device_count == 0:
            return None
        
        # 获取第一个GPU的信息
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        name = pynvml.nvmlDeviceGetName(handle)
        
        return {
            "name": name.decode('utf-8'),
            "memory_total": info.total // (1024 ** 2),  # MB
            "memory_free": info.free // (1024 ** 2),
            "memory_used": info.used // (1024 ** 2)
        }
    except:
        return None

def get_model_info(model_path):
    """从文件名解析模型信息"""
    filename = os.path.basename(model_path)
    
    # 解析模型参数大小 (e.g., "llama-7b", "mixtral-8x7b")
    parameters = "?"
    if "7b" in filename.lower():
        parameters = "7"
    elif "8b" in filename.lower():
        parameters = "8"
    elif "13b" in filename.lower():
        parameters = "13"
    elif "30b" in filename.lower():
        parameters = "30"
    elif "70b" in filename.lower():
        parameters = "70"
    
    # 解析量化类型 (e.g., "Q4_K_M")
    quantization = "?"
    if "q2_k" in filename.lower():
        quantization = "Q2_K"
    elif "q3_k" in filename.lower():
        quantization = "Q3_K"
    elif "q4_k" in filename.lower():
        quantization = "Q4_K"
    elif "q5_k" in filename.lower():
        quantization = "Q5_K"
    elif "q6_k" in filename.lower():
        quantization = "Q6_K"
    elif "q8_0" in filename.lower():
        quantization = "Q8_0"
    
    return {
        "parameters": parameters,
        "quantization": quantization
    }
    
def format_file_types(file_types):
    """
    格式化文件类型列表为字符串
    :param file_types: 文件类型列表
    :return: 格式化后的字符串
    """
    return " ".join([f"*.{ext.strip('.')}" for ext in file_types])

def get_resource_path(relative_path):
    """获取资源文件路径，兼容打包和开发环境"""
    try:
        # PyInstaller 打包后的路径
        base_path = sys._MEIPASS
    except AttributeError:
        # 开发环境路径
        base_path = Path.cwd()
    
    return os.path.join(base_path, relative_path)

def get_filename(file_path: str, without_extension: bool = False) -> str:
    """从文件路径中获取文件名"""
    filename = os.path.basename(file_path)
    if without_extension:
        filename = os.path.splitext(filename)[0]
    return filename

def string_to_base64(text: str) -> str:
    """将字符串编码为 Base64"""
    text_bytes = text.encode('utf-8')
    base64_bytes = base64.b64encode(text_bytes)
    base64_string = base64_bytes.decode('utf-8')
    return base64_string

def base64_to_string(base64_string: str) -> str:
    """将 Base64 解码为字符串"""
    base64_bytes = base64_string.encode('utf-8')
    text_bytes = base64.b64decode(base64_bytes)
    text = text_bytes.decode('utf-8')
    return text

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
    
def safe_read_file(file_path) -> str:
    """自动检测编码并读取文件"""
    # 先检测编码
    with open(file_path, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        confidence = result['confidence']
    
    print(f"检测到编码: {encoding}, 置信度: {confidence:.2f}")
    
    # 使用检测到的编码读取
    with open(file_path, 'r', encoding=encoding) as f:
        return f.read()