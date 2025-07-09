import customtkinter as ctk
from customtkinter import filedialog
from service import localization

class OptionsDialog(ctk.CTkToplevel):
    def __init__(self, parent, settings_data):
        super().__init__(parent)
        
        self.parent = parent
        self.settings_data = settings_data
        self.result = None
        
        # 设置对话框属性
        self.title(localization.get("advanced_settings"))
        self.geometry("360x240")
        self.resizable(False, False)
        
        # 设置为模态对话框
        self.transient(parent)
        self.grab_set()
        
        # 居中显示
        self.center_window()
        
        # 创建界面
        self.create_widgets()
        
        # 初始化值
        self.load_settings()
    
    def center_window(self):
        """将对话框居中显示"""
        self.update_idletasks()
        width = 520
        height = 520
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        """创建对话框界面"""
        # 主框架
        main_frame = ctk.CTkFrame(self,fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 配置主框架的网格权重
        main_frame.grid_columnconfigure(0, weight=0, minsize=120)  # 固定标签列宽度
        main_frame.grid_columnconfigure(1, weight=1)              # 控件列可扩展
        main_frame.grid_columnconfigure(2, weight=0) 
        
        # 标题
        title_label = ctk.CTkLabel(main_frame, text=localization.get("advanced_settings"), 
                                font=ctk.CTkFont(size=18, weight="bold"))
        title_label.grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 20), sticky="w")
        
        # 主题设置        
        theme_label = ctk.CTkLabel(main_frame, text=localization.get("theme") + ":", 
                                font=ctk.CTkFont(size=12, weight="bold"))
        theme_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        
        self.appearance_var = ctk.StringVar(value="dark")
        self.appearance_menu = ctk.CTkOptionMenu(
            main_frame,
            values=["system", "dark", "light"],
            variable=self.appearance_var,
            width=150
        )
        self.appearance_menu.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        # 模型文件设置
        model_label = ctk.CTkLabel(main_frame, text=localization.get("model_file"), 
                                font=ctk.CTkFont(size=12, weight="bold"))
        model_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        
        self.model_var = ctk.StringVar()
        model_entry = ctk.CTkEntry(main_frame, textvariable=self.model_var, 
                                placeholder_text=localization.get("select_model_file"))
        model_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        
        model_browse = ctk.CTkButton(main_frame, text=localization.get("browse"), 
                                    command=self.browse_model, width=60)
        model_browse.grid(row=2, column=2, padx=(0, 10), pady=10)
        
        # ===== 反思设置区域 =====
        translation_section = ctk.CTkFrame(main_frame)
        translation_section.grid(row=3, column=0, columnspan=3, sticky="ew", pady=15)
        translation_section.grid_columnconfigure(1, weight=1)
        
        # 反思设置标题
        reflection_title = ctk.CTkLabel(translation_section, 
                                    text=localization.get("translation_options"), 
                                    font=ctk.CTkFont(size=14, weight="bold"))
        reflection_title.grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 10), sticky="w")
        
        # 反思复选框
        self.reflection_var = ctk.BooleanVar(value=True)  # 默认开启
        self.reflection_checkbox = ctk.CTkCheckBox(
            translation_section,
            text=localization.get("enable_reflection"),
            variable=self.reflection_var
        )
        self.reflection_checkbox.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 10), sticky="w")
        
        # 反思说明
        reflection_tips = ctk.CTkLabel(translation_section, 
                                    text=localization.get("reflection_tips"), 
                                    font=ctk.CTkFont(size=10), 
                                    text_color=("gray50", "gray70"),
                                    wraplength=400,
                                    anchor="w", 
                                    justify="left")
        reflection_tips.grid(row=2, column=0, columnspan=2, padx=15, pady=(0, 15), sticky="w")
        
        # # GPU设置标题
        # gpu_title = ctk.CTkLabel(main_frame, text="GPU设置:", 
        #                         font=ctk.CTkFont(size=12, weight="bold"))
        # gpu_title.grid(row=3, column=0, padx=10, pady=(20, 5), sticky="w")
        
        # GPU层数
        gpu_label = ctk.CTkLabel(translation_section, text=localization.get("gpu_layers"))
        gpu_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        
        # GPU滑块容器
        slider_frame = ctk.CTkFrame(translation_section, fg_color="transparent")
        slider_frame.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        slider_frame.grid_columnconfigure(0, weight=1)
        
        self.gpu_layers_var = ctk.StringVar(value="0")
        self.gpu_slider = ctk.CTkSlider(
            slider_frame,
            from_=-1, to=127,
            number_of_steps=128,
            command=self.update_gpu_value
        )
        self.gpu_slider.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        self.gpu_value_label = ctk.CTkLabel(slider_frame, text=localization.get("cpu_only"))
        self.gpu_value_label.grid(row=0, column=1, sticky="e")
        
        # GPU帮助说明
        gpu_help = ctk.CTkLabel(translation_section, text=localization.get("gpu_tips"), 
                            font=ctk.CTkFont(size=10), text_color=("gray50", "gray70"))
        gpu_help.grid(row=5, column=0, columnspan=3, padx=10, pady=(0, 20), sticky="w")
        
        # 分隔线
        separator = ctk.CTkFrame(main_frame, height=2)
        separator.grid(row=6, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
        
        # 按钮区域
        button_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_container.grid(row=7, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
        button_container.grid_columnconfigure(0, weight=1)
        
        # 取消按钮
        cancel_button = ctk.CTkButton(button_container, text=localization.get("cancel"), command=self.cancel_clicked, width=100)
        cancel_button.grid(row=0, column=1, padx=5)
        
        # 确定按钮
        ok_button = ctk.CTkButton(button_container, text=localization.get("ok"), command=self.ok_clicked, width=100)
        ok_button.grid(row=0, column=2, padx=5)
    
    def load_settings(self):
        """加载当前设置"""
        if 'appearance_mode' in self.settings_data:
            self.appearance_var.set(self.settings_data['appearance_mode'])
        if 'model_path' in self.settings_data:
            self.model_var.set(self.settings_data['model_path'])
        if 'gpu_layers' in self.settings_data:
            gpu_layers = int(self.settings_data['gpu_layers'])
            self.gpu_layers_var.set(str(gpu_layers))
            self.gpu_slider.set(gpu_layers)
            self.update_gpu_value(gpu_layers)
            
        if 'reflection_enabled' in self.settings_data:
            self.reflection_var.set(self.settings_data['reflection_enabled'])
    
    def update_gpu_value(self, value):
        """更新GPU值显示"""
        value = int(value)
        self.gpu_layers_var.set(str(value))
        
        if value == 0:
            label_text = localization.get("cpu_only")
        elif value == -1:
            label_text = localization.get("gpu_full")
        else:
            label_text = f"{value} {localization.get('layer')}"
            
        self.gpu_value_label.configure(text=label_text)
    
    def browse_model(self):
        """浏览模型文件"""
        filename = filedialog.askopenfilename(
            title=localization.get("select_model_file"),
            filetypes=[
                (localization.get("model_files"), "*.gguf *.ggml *.bin"),
                (localization.get("all_files"), "*.*")
            ]
        )
        if filename:
            self.model_var.set(filename)
    
    def ok_clicked(self):
        """确定按钮点击"""
        self.result = {
            'appearance_mode': self.appearance_var.get(),
            'model_path': self.model_var.get(),
            'gpu_layers': self.gpu_layers_var.get(),
            'reflection_enabled': self.reflection_var.get()  # 添加反思设置
        }
        self.destroy()
    
    def cancel_clicked(self):
        """取消按钮点击"""
        self.result = None
        self.destroy()