import os
import queue
import threading
from pathlib import Path
from tkinter import messagebox
import traceback
import customtkinter as ctk
from customtkinter import filedialog
from main import process_video_file,settings,get_logger,utils
from service import localization
from defs import FileType, get_supported_subtitle_types, get_supported_video_types
from gui.options_dialog import OptionsDialog
import utils
import sys
from gui.glossary_dialog import GlossaryDialog
from toolz import pipe
import info

class LightVTGUI:
    """LightVT GUI界面类"""
    logger = get_logger("LightVT")
    def __init__(self, root):
        self.root = root
        self.root.title(f"LightVT - {info.APP_VERSION}")
        self.root.geometry("650x700")
        self.root.minsize(650, 700)
        # self.root.iconbitmap(utils.get_resource_path("assets/icon.ico"))  # 设置窗口图标
        # 仅在 Windows 下设置 .ico 图标
        if sys.platform.startswith("win"):
            self.root.iconbitmap(utils.get_resource_path("assets/icon.ico"))
        elif sys.platform == "darwin":
            # macOS 可选：不设置或用 .icns（Tkinter 不直接支持 .icns）
            pass
        
        # 设置颜色主题和外观模式
        ctk.set_appearance_mode("dark")  # 跟随系统主题 ("dark", "light", "system")
        ctk.set_default_color_theme("blue")  # 可选: "blue", "green", "dark-blue"
        
        # 创建队列用于线程间通信
        self.message_queue = queue.Queue()
        
        localization.init(lang="zh-CN")
        
        # 添加选项设置的实例变量
        self.appearance_mode = "dark"
        self.model_var = ctk.StringVar(value="models/Qwen3-8B-GGUF")  # 默认模型路径
        self.gpu_layers_var = ctk.StringVar(value="0")
        self.reflection_enabled_var = ctk.BooleanVar(value=True)  # 默认启用反思
        
        # 创建界面
        self.create_widgets()
        self.restore_last_settings()
        
        # 启动消息处理
        self.process_queue()

        # 测试日志显示
        self.log_message("GUI已初始化")
        self.log_message("请选择输入文件并设置选项")
        
    def open_options_dialog(self):
        """打开选项对话框"""
        # 准备当前设置数据
        settings_data = {
            'appearance_mode': self.appearance_mode,
            'model_path': self.model_var.get(),
            'gpu_layers': self.gpu_layers_var.get(),
            'reflection_enabled': self.reflection_enabled_var.get()  # 添加反思设置
        }
        
        # 创建并显示对话框
        dialog = OptionsDialog(self.root, settings_data)
        self.root.wait_window(dialog)
        
        # 处理对话框结果
        if dialog.result:
            self.apply_options(dialog.result)
            
    def apply_options(self, options):
        """应用选项设置"""
        # 应用主题
        if options['appearance_mode'] != self.appearance_mode:
            self.appearance_mode = options['appearance_mode']
            ctk.set_appearance_mode(options['appearance_mode'])
        
        # 应用模型路径
        self.model_var.set(options['model_path'])
        settings.set_model_path(options['model_path'])
        
        # 应用反思设置
        self.reflection_enabled_var.set(options['reflection_enabled'])
        settings.set_reflection_enabled(self.reflection_enabled_var.get())
        
        # 应用GPU设置
        self.gpu_layers_var.set(options['gpu_layers'])
        settings.set_gpu_layers(int(options['gpu_layers']))
        
        self.log_message(localization.get("options_applied"))
        
    def create_widgets(self):
        """"创建GUI组件"""
        
        # 清空当前界面上的所有组件
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # 主容器 - 使用网格布局
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(5, weight=1)  # 日志区域可扩展
        
        # 标题区域
        title_frame = ctk.CTkFrame(self.root, corner_radius=0, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        title_label = ctk.CTkLabel(title_frame, text=localization.get("title"), 
            font=ctk.CTkFont(size=24, weight="bold"))
        title_label.pack(side="left")
        
        subtitle_label = ctk.CTkLabel(title_frame, text=localization.get("subtitle"), 
            font=ctk.CTkFont(size=12))
        subtitle_label.pack(side="left", padx=(10, 0), pady=5)
        
        # 选项按钮
        self.options_button = ctk.CTkButton(
            title_frame,
            text="⚙️",
            command=self.open_options_dialog,
            width=40,
            height=32,
            font=ctk.CTkFont(size=16)
        )
        self.options_button.pack(side="right", padx=(10, 0))
        
        # 术语表按钮
        self.glossary_button = ctk.CTkButton(
            title_frame,
            text="📚",
            command=self.open_glossary_dialog,
            width=40,
            height=32,
            font=ctk.CTkFont(size=16)
        )
        self.glossary_button.pack(side="right", padx=(10, 0))
        
        # 增加语言选择下拉菜单
        current_lang_code = localization.get_current_language()
        lang_display_map = {
            "en": "English",
            "zh-CN": "简体中文",
            "zh-TW": "繁體中文"
        }
        default_lang = lang_display_map.get(current_lang_code, "简体中文")
        self.language_var = ctk.StringVar(value=default_lang)  # 默认语言为简体中文
        self.language_menu = ctk.CTkOptionMenu(
            title_frame,
            values=["English", "简体中文", "繁體中文"],
            variable=self.language_var,
            command=self.set_language
        )
        self.language_menu.pack(side="right", padx=(10, 10))
        
        # ===== 文件设置区域 =====
        file_frame = ctk.CTkFrame(self.root)
        file_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        # 为frame添加标题
        file_label = ctk.CTkLabel(file_frame, text=localization.get("file_settings"), 
            font=ctk.CTkFont(size=14, weight="bold"))
        file_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))
        
        # 设置网格列权重
        file_frame.columnconfigure(1, weight=1)
        
        # 输入文件
        ctk.CTkLabel(file_frame, text=localization.get("input_file")).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.input_var = ctk.StringVar()
        input_entry = ctk.CTkEntry(file_frame, textvariable=self.input_var, placeholder_text=localization.get("select_video_or_subtitle_file"))
        input_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        input_browse = ctk.CTkButton(file_frame, text= localization.get("browse"), command=self.browse_input, width=80)
        input_browse.grid(row=1, column=2, padx=10, pady=10)
        
        # 输出文件
        ctk.CTkLabel(file_frame, text=localization.get("output_file")).grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.output_var = ctk.StringVar()
        output_entry = ctk.CTkEntry(file_frame, textvariable=self.output_var, placeholder_text=localization.get("select_output_file"))
        output_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        output_browse = ctk.CTkButton(file_frame, text= localization.get("browse"), command=self.browse_output, width=80)
        output_browse.grid(row=2, column=2, padx=10, pady=10)
        
        # ===== 选项设置区域 =====
        options_frame = ctk.CTkFrame(self.root)
        options_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        # 为frame添加标题
        options_label = ctk.CTkLabel(options_frame, text=localization.get("translation_options"), 
                                    font=ctk.CTkFont(size=14, weight="bold"))
        options_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))
        
        options_frame.columnconfigure(1, weight=1)
        options_frame.columnconfigure(3, weight=1)
        
        # 语言选择
        iso_to_lang = localization.get("iso_to_lang")
        ctk.CTkLabel(options_frame, text=localization.get("source_language")).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.source_lang_var = ctk.StringVar(value=iso_to_lang["auto"])
        source_combo = ctk.CTkOptionMenu(
            options_frame, 
            values=[
                iso_to_lang["auto"],
                # iso_to_lang["en"],
                # iso_to_lang["zh-CN"],
                # iso_to_lang["zh-TW"],
                # iso_to_lang["ja"],
                # iso_to_lang["ko"],
                # iso_to_lang["fr"],
                # iso_to_lang["de"],
                # iso_to_lang["es"],
                # iso_to_lang["it"],
                # iso_to_lang["ru"]
            ],
            variable=self.source_lang_var,
            width=120
        )
        source_combo.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        ctk.CTkLabel(options_frame, text=localization.get("target_language")).grid(row=1, column=2, padx=10, pady=10, sticky="w")
        self.target_lang_var = ctk.StringVar(value=iso_to_lang["zh-CN"])
        target_combo = ctk.CTkOptionMenu(
            options_frame, 
            values=[
                iso_to_lang["en"],
                iso_to_lang["zh-CN"],
                iso_to_lang["zh-TW"],
                iso_to_lang["ja"],
                iso_to_lang["ko"],
                iso_to_lang["fr"],
                iso_to_lang["de"],
                iso_to_lang["es"],
                iso_to_lang["it"],
                iso_to_lang["ru"]
            ],
            variable=self.target_lang_var,
            width=120
        )
        target_combo.grid(row=1, column=3, padx=10, pady=10, sticky="w")
        
        # 处理模式选择
        processing_mode_k2v = localization.get("processing_mode_k2v")
        ctk.CTkLabel(options_frame, text=localization.get("processing_mode")).grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.processing_mode_var = ctk.StringVar(value=processing_mode_k2v["translate"])  # 默认选项为"翻译"
        self.processing_mode_menu = ctk.CTkOptionMenu(
            options_frame,
            values=[
                processing_mode_k2v["translate"],
                processing_mode_k2v["extract_subtitle"]
            ],
            variable=self.processing_mode_var,
            width=120
        )
        self.processing_mode_menu.grid(row=2, column=1, padx=10, pady=(10, 15), sticky="w")
        
        # ===== 控制按钮区域 =====
        control_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        control_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        # 进度条
        self.progress_var = ctk.StringVar(value=localization.get("ready"))
        progress_label = ctk.CTkLabel(control_frame, textvariable=self.progress_var)
        progress_label.grid(row=0, column=0, columnspan=3, padx=10, pady=(0, 5), sticky="w")
        
        self.progress_bar = ctk.CTkProgressBar(control_frame)
        self.progress_bar.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 15), sticky="ew")
        self.progress_bar.set(0)  # 初始状态
        
        # 按钮
        button_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        button_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=5)
        
        self.start_button = ctk.CTkButton(
            button_frame, 
            text=localization.get("start_processing"), 
            command=self.start_processing,
            width=120,
            height=32,
            fg_color=("#3a7ebf", "#1f538d"),  # 蓝色
            hover_color=("#325882", "#14375e")
        )
        self.start_button.grid(row=0, column=0, padx=(0, 10))
        
        self.stop_button = ctk.CTkButton(
            button_frame, 
            text=localization.get("stop_processing"), 
            command=self.stop_processing,
            width=120,
            height=32,
            fg_color=("#bf3a3a", "#8d1f1f"),  # 红色
            hover_color=("#822525", "#3e1414"),
            state="disabled"
        )
        self.stop_button.grid(row=0, column=1, padx=(0, 10))
        
        self.clear_button = ctk.CTkButton(
            button_frame, 
            text=localization.get("clear_log"), 
            command=self.clear_log,
            width=120,
            height=32
        )
        self.clear_button.grid(row=0, column=2)
        
        # ===== 日志区域 =====
        log_frame = ctk.CTkFrame(self.root)  # 添加一个框架使文本框更明显
        log_frame.grid(row=5, column=0, padx=20, pady=(5, 20), sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)
        
        self.log_text = ctk.CTkTextbox(
            log_frame, 
            height=200, 
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",  # 添加自动换行
            border_width=1  # 添加边框使文本框更明显
        )
        self.log_text.grid(row=0, column=0, padx=1, pady=1, sticky="nsew")
        
        # 添加初始文本使文本框可见
        self.log_text.insert("1.0", localization.get("log_ready"))
        
        # 状态栏
        status_frame = ctk.CTkFrame(self.root, fg_color="transparent", height=20)
        status_frame.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        version_label = ctk.CTkLabel(status_frame, text="LightVT © 2025", 
                                   font=ctk.CTkFont(size=10), text_color=("gray50", "gray70"))
        version_label.pack(side="right")
        
        # 处理线程
        self.processing_thread = None
        self.stop_event = threading.Event()
        
    def open_glossary_dialog(self):
        """打开术语表对话框"""
        dialog = GlossaryDialog(self.root, 
                                filename=self.input_var.get(),
                                input_path=self.input_var.get(),
                                model_path=self.model_var.get(),
                                target_lang=self.target_lang_var.get())
        self.root.wait_window(dialog)
        
        # 术语表更新后的处理（如果需要）
        self.log_message("术语表已更新")
        
    def set_language(self, lang: str):
        """切换语言"""
        language_map = {
            "English": "en",
            "简体中文": "zh-CN",
            "繁體中文": "zh-TW"
        }
        selected_language = language_map.get(lang, "en")  # 默认语言为简体中文
        localization.set_language(selected_language)
        self.create_widgets()  # 重新创建界面以应用语言更改
        self.restore_last_settings()

    def restore_last_settings(self):
        """恢复上次设置"""
        self.input_var.set(settings.get_input_path())
        self.output_var.set(settings.get_output_path())
        self.model_var.set(settings.get_model_path())
        
        iso_to_lang = localization.get("iso_to_lang")
        self.source_lang_var.set(iso_to_lang[settings.get_source_language()])
        self.target_lang_var.set(iso_to_lang[settings.get_target_language()])
        
        processing_mode_k2v = localization.get("processing_mode_k2v")
        self.processing_mode_var.set(processing_mode_k2v[settings.get_processing_mode()])
        
        # 恢复反思设置
        self.reflection_enabled_var.set(settings.get_reflection_enabled())
    
        # 恢复GPU设置
        gpu_layers = settings.get_gpu_layers()
        self.gpu_layers_var.set(str(gpu_layers))
        
    def save_current_settings(self):
        """保存当前设置到配置文件"""
        try:
            # 保存文件路径设置
            if hasattr(self, 'input_var'):
                settings.set_input_path(self.input_var.get())
            
            if hasattr(self, 'output_var'):
                settings.set_output_path(self.output_var.get())
            
            # 保存模型设置
            if hasattr(self, 'model_var'):
                settings.set_model_path(self.model_var.get())
            
            lang_to_iso = localization.get("lang_to_iso")
            # 保存语言设置
            if hasattr(self, 'source_lang_var'):
                iso_source_lang = lang_to_iso[self.source_lang_var.get()]
                settings.set_source_language(iso_source_lang)
            
            if hasattr(self, 'target_lang_var'):
                iso_target_lang = lang_to_iso[self.target_lang_var.get()]
                settings.set_target_language(iso_target_lang)
            
            # 保存界面语言设置
            if hasattr(self, 'localization'):
                current_lang = localization.get_current_language()
                settings.set_interface_language(current_lang)
            
            # 保存反思设置
            if hasattr(self, 'reflection_enabled'):
                settings.set_reflection_enabled(self.reflection_enabled)
            
            # 保存GPU设置
            if hasattr(self, 'gpu_layers_var'):
                gpu_layers = int(self.gpu_layers_var.get())
                settings.set_gpu_layers(gpu_layers)
            
            # 保存主题设置
            if hasattr(self, 'appearance_mode'):
                settings.set_appearance_mode(self.appearance_mode)
            
            # 保存处理模式设置
            processing_mode_v2k = localization.get("processing_mode_v2k")
            if hasattr(self, 'processing_mode_var'):
                settings.set_processing_mode(processing_mode_v2k[self.processing_mode_var.get()])
            
            
            # 强制保存到文件
            settings.save()
            
        except Exception as e:
            error_msg = localization.get('error_saving_settings')
            self.log_message(f"{error_msg} {str(e)}")
            error_details = traceback.format_exc()
            self.logger.error(f"{error_msg}: {str(error_details)}")
    
    def change_appearance_mode(self, mode):
        mode_dict = {"系统": "system", "暗色": "dark", "亮色": "light"}
        ctk.set_appearance_mode(mode_dict[mode])
    
    def browse_input(self):
        filename = filedialog.askopenfilename(
            title=localization.get("select_video_or_subtitle_file"),
            filetypes=[
                (
                    localization.get("video_files"), 
                    utils.format_file_types(get_supported_video_types())
                ),
                (
                    localization.get("subtitle_files"), 
                    utils.format_file_types(get_supported_subtitle_types())
                ),
                (localization.get("all_files"), "*.*")
            ]
        )
        if filename:
            self.input_var.set(filename)
            settings.set_input_path(filename)
            # 自动设置输出文件名
            if not settings.get_output_path():
                target_lang_value = self.target_lang_var.get()
                lang_to_iso = localization.get("lang_to_iso")
                target_lang = lang_to_iso.get(target_lang_value, "zh-CN")
                output_path = settings.auto_set_output_path(filename, target_lang)
                settings.set_output_path(output_path)
                self.output_var.set(output_path)
                
            # 判断文件类型并自动设置处理模式
            processing_mode_k2v = localization.get("processing_mode_k2v")
            if filename.lower().endswith(get_supported_subtitle_types()):
                self.processing_mode_var.set(processing_mode_k2v["translate"])  # 字幕文件设置为翻译模式
    
    def browse_output(self):
        filename = filedialog.asksaveasfilename(
            title=localization.get("select_output_file"),
            defaultextension=".srt",
            filetypes=[
                (
                    localization.get("subtitle_files"), 
                    utils.format_file_types(get_supported_subtitle_types())
                ), 
                (localization.get("all_files"), "*.*")]
        )
        if filename:
            self.output_var.set(filename)
            settings.set_output_path(filename)
    
    def log_message(self, message, progress_var=None):
        """添加消息到日志"""
        if message is None or message.strip() == "":
            return
        self.message_queue.put(message)
    
    def process_queue(self):
        """处理消息队列"""
        try:
            while True:
                message = self.message_queue.get_nowait()

                self.logger.info(message)
                
                # 插入到文本框
                self.log_text.insert("end", f"{message}\n")
                self.log_text.see("end")
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)
    
    def clear_log(self):
        self.log_text.delete("0.0", "end")
    
    def start_processing(self):
        # 验证输入
        if not self.input_var.get():
            messagebox.showerror(localization.get("error"), 
                                 localization.get("please_select_input_error"))
            return
        
        if not self.output_var.get():
            messagebox.showerror(localization.get("error"), 
                                localization.get("please_select_output_error"))
            return
        
        # 根据处理模式和文件类型验证模型路径
        processing_mode = self.processing_mode_var.get()
        
        # 如果是翻译模式，或者是视频文件且不是仅提取模式，需要模型
        processing_mode_v2k = localization.get("processing_mode_v2k")
        if processing_mode_v2k[processing_mode] == "translate":
            if not self.model_var.get():
                messagebox.showerror(localization.get("error"), 
                                    localization.get("translation_mode_error"))
                return
        
        # 禁用开始按钮，启用停止按钮
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        
        # 启动进度条
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        self.progress_var.set(localization.get("processing"))
        
        # 重置停止事件
        self.stop_event.clear()
        
        # 自动保存当前设置
        self.save_current_settings()
        
        # 启动处理线程
        self.processing_thread = threading.Thread(target=self.process_file)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def stop_processing(self):
        self.stop_event.set()
        self.stop_button.configure(state="disabled")
        self.progress_var.set(localization.get("stopping"))
        self.log_message(localization.get("user_stop_processing"))
    
    def process_file(self):
        """在后台线程中处理文件"""
        try:
            # 确定是否为仅提取模式
            processing_mode_k2v = localization.get("processing_mode_k2v")
            extract_only = (self.processing_mode_var.get() == processing_mode_k2v["extract_subtitle"])
            
            # 这里调用您的原始处理逻辑
            args = {
                'input': self.input_var.get(),
                'output': self.output_var.get(),
                'model_path': self.model_var.get(),
                'source_lang': self.source_lang_var.get(),
                'target_lang': self.target_lang_var.get(),
                'extract_only': extract_only,
                'gpu_layers': int(self.gpu_layers_var.get()),
                'reflection_enabled': self.reflection_enabled_var.get(),  # 添加反思参数
                'stop_event': self.stop_event,
                'log_callback': self.log_message
            }
            
            msg_start_processing = localization.get("msg_start_processing")
            self.log_message(f"{msg_start_processing} {args['input']}")
            
            # 调用处理函数
            process_video_file(args)
            
            if self.stop_event.is_set():
                self.log_message(localization.get("msg_processing_stopped"))
                self.progress_var.set(localization.get("stopped"))
            else:
                self.log_message(localization.get("msg_processing_complete"))
                self.progress_var.set(localization.get("completed"))
                messagebox.showinfo(localization.get("completed"), f"{localization.get('msg_processing_complete_detail')} {args['output']}")
                
        except Exception as e:
            error_details = traceback.format_exc()
            self.log_message(f"{localization.get('error')}: {str(error_details)}")
            self.progress_var.set(localization.get("error"))
            messagebox.showerror(localization.get("error"), f"{localization.get('error_processing_failed')} {str(e)}")
        
        finally:
            # 恢复UI状态
            self.root.after(0, self.reset_ui)
    
    def reset_ui(self):
        """重置UI状态"""
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.progress_bar.stop()
        self.progress_bar.set(0)

def main():
    # 设置高DPI支持
    # ctk.deactivate_automatic_dpi_awareness()
    
    # 创建窗口
    root = ctk.CTk()
    app = LightVTGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()