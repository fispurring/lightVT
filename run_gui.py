import sys
from pathlib import Path

# 添加当前目录到系统路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

import os
import sys

if getattr(sys, 'frozen', False):
    # 如果是打包环境，切换到资源目录
    os.chdir(os.path.dirname(sys.executable))
    # 添加自带ffmpeg目录到 PATH
    os.environ["PATH"] += os.pathsep + f"{sys._MEIPASS}/bin"
    # 添加 ffprobe 所在目录到 PATH
    os.environ["PATH"] += os.pathsep + "/usr/local/bin" + os.pathsep + "/opt/homebrew/bin"
    
    # 将日志输出到文件
    # log_dir = Path(os.path.dirname(sys.executable)) / "logs"
    # log_dir.mkdir(exist_ok=True)
    
    # sys.stdout = open(log_dir / "output.log", "w", encoding="utf-8")
    # sys.stderr = open(log_dir / "error.log", "w", encoding="utf-8")

# 导入并运行GUI
from gui import main

if __name__ == "__main__":
    main()