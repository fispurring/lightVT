import sys
import os
from pathlib import Path
import pynvml

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