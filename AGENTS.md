# LightVT 项目概览

## 基本信息
LightVT 是一款轻量级视频字幕翻译工具（v0.4.1），支持 Windows/Linux/macOS，提供 GUI 和 CLI 双模式。

## 核心架构
- **main.py**: CLI 入口，默认启动 GUI，支持 `--input`/`--output` 命令行模式
- **gui/**: CustomTkinter 图形界面，包含主窗口、选项对话框、术语表对话框
- **interface/**: 业务逻辑层，负责文件处理流程编排和术语表生成
- **service/extractor**: 基于 FFmpeg 的视频字幕提取服务
- **service/translator**: 基于 llama.cpp 的本地 LLM 翻译服务，支持 SRT 和纯文本
- **service/glossary**: AI 驱动的术语表管理，保障翻译一致性
- **service/localization**: 多语言支持（中/英/繁）
- **utils/settings**: 配置持久化存储

## 处理流程
1. 字幕提取: 视频文件 → FFmpeg → SRT 字幕
2. 字幕翻译: SRT/视频 → LLM 推理 → 目标语言字幕
3. 纯文本翻译: .txt → LLM → 翻译结果

## 关键依赖
- customtkinter (GUI框架)
- llama_cpp_python (本地推理)
- ffmpeg-python (多媒体处理)
- srt (字幕解析)

## 技术特点
- 支持 CUDA GPU 加速
- 按文件名自动加载术语表
- 翻译质量可通过 LLM 自我反思机制优化
- 多语言界面通过 `localization.get()` 访问

## 要求
- 安装的llama-cpp-python必须支持cuda