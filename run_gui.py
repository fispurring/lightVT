import sys
from pathlib import Path

# 添加当前目录到系统路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 导入并运行GUI
from gui import main

if __name__ == "__main__":
    main()