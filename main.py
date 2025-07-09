import argparse
import sys
from pathlib import Path
from interface import process_video_file, get_file_type
from service.log import get_logger
import service.settings as settings
import utils

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='LightVT - 视频字幕翻译工具')
    parser.add_argument('--gui', action='store_true', help='启动GUI界面')
    parser.add_argument('--input', '-i', help='输入文件路径')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--model-path', '-m', help='模型路径')
    parser.add_argument('--source-lang', default='英语', help='源语言')
    parser.add_argument('--target-lang', default='简体中文', help='目标语言')
    parser.add_argument('--extract-only', action='store_true', help='仅提取字幕')
    parser.add_argument('--translate-only', action='store_true', help='仅翻译字幕')
    parser.add_argument('--gpu-layers', type=int, default=0, help='GPU层数')
    
    args = parser.parse_args()
    
    if args.gui or len(sys.argv) == 1:
        # 启动GUI
        from gui import main as gui_main
        gui_main()
    else:
        # 命令行模式
        if not args.input or not args.output:
            print("错误: 命令行模式需要指定输入和输出文件")
            parser.print_help()
            return
        
        result = process_video_file(vars(args))
        if result:
            print("处理完成!")
        else:
            print("处理失败!")

if __name__ == "__main__":
    main()

__all__ = [
    "get_logger",
    "process_video_file",
    "settings",
    "utils"
]