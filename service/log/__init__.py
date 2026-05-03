import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Dict
import os
import threading

try:
    from concurrent_log_handler import ConcurrentRotatingFileHandler
    HasConcurrentHandler = True
except ImportError:
    HasConcurrentHandler = False

lock = threading.Lock()
loggerDict: Dict[str,logging.Logger] = {}

def setup_logger(name: str = "LightVT", log_file: str = "app.log", level: int = logging.DEBUG):
    """设置同时输出到控制台和文件的日志器"""
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)  # 确保目录存在
    
    # 创建日志器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建格式器
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # 按时间轮转的文件处理器
    log_path = f"{log_dir}/{log_file}"
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=str(log_path),
        when='midnight',        # 轮转时机
        interval=1,            # 轮转间隔
        backupCount=30,        # 保留文件数量
        encoding='utf-8',
        delay=False,
        utc=False
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # 设置轮转文件名后缀
    file_handler.suffix = "%Y-%m-%d"

    # 自定义轮转函数，处理 Windows 多线程写入时的 PermissionError
    def safe_rotator(source, destination):
        try:
            if os.path.exists(source):
                os.rename(source, destination)
        except PermissionError:
            pass

    file_handler.rotator = safe_rotator
    
    # 添加处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

def get_logger(name: str = "LightVT") -> logging.Logger:
    """获取已设置的日志器"""
    with lock:
        logger = loggerDict.get(name)
        if logger is None:
            logger = loggerDict[name] = setup_logger(name)
        return logger

__all__ = ["get_logger"]
