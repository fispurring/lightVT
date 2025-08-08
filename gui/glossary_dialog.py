# lightVT/gui/glossary_dialog.py
"""
术语表编辑对话框 - 使用 tksheet 实现 Excel 风格表格
"""

import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk
from tksheet import Sheet
from service import glossary
from service import localization
from service.log import get_logger
from interface import generate_glossary
import threading
import queue

logger = get_logger("GlossaryDialog")

class GlossaryDialog(ctk.CTkToplevel):
    """术语表编辑对话框 - tksheet 版本"""
    
    def __init__(self, parent, filename: str, input_path:str, model_path: str, target_lang: str,n_gpu_layers: int = -1):
        super().__init__(parent)
        
        self.filename = filename
        self.input_path = input_path
        self.model_path = model_path
        self.target_lang = target_lang
        self.n_gpu_layers = n_gpu_layers
        
        self.message_queue = queue.Queue()

        self.title(localization.get("glossary_management"))
        self.geometry("640x800")
        self.minsize(640, 800)
        
        # 设置模态
        self.transient(parent)
        self.grab_set()
        
        # 居中显示
        self.center_window()
        
        # 初始化数据
        glossary.load_glossary(glossary.to_glossary_filename(self.filename))
        self.glossary_data = glossary.get_terms()
        self.has_changes = False
        
        # 创建界面
        self.create_widgets()
        self.load_data()
        
        self.stop_event = threading.Event()
        self.process_thread = None
        
        # 绑定关闭事件
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 启动处理队列
        self.process_queue()
    
    def center_window(self):
        """相对于父窗口居中"""
        self.update_idletasks()
        
        # 获取父窗口位置和大小
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()
        
        # 获取当前窗口大小
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()
        
        # 计算居中位置
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        # 确保窗口不会超出屏幕边界
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        x = max(0, min(x, screen_width - dialog_width))
        y = max(0, min(y, screen_height - dialog_height))
        
        self.geometry(f"+{x}+{y}")
    
    def create_widgets(self):
        """创建界面组件"""
        
        # 主框架
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 🎨 顶部信息栏
        self.create_header_section(main_frame)
        
        # 🎨 工具栏
        self.create_toolbar_section(main_frame)
        
        # 🎨 表格区域 - 主要内容
        self.create_table_section(main_frame)
        
        # 🎨 底部按钮栏
        self.create_button_section(main_frame)
    
    def create_header_section(self, parent):
        """创建顶部信息栏 - 紧凑版"""
        header_frame = ctk.CTkFrame(parent, height=90, corner_radius=10)  # 🔥 减少高度
        header_frame.pack(fill="x", pady=(0, 12))
        header_frame.pack_propagate(False)
        
        # 左侧标题
        left_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="y", padx=15, pady=12)
        left_frame.pack_propagate(True) 
        
        title_label = ctk.CTkLabel(
            left_frame, 
            text=f"📚 {localization.get('glossary_management')}", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(anchor="w")
        
        subtitle_label = ctk.CTkLabel(
            left_frame,
            width=330,
            height=80,
            wraplength=330,
            text=localization.get("glossary_dialog_tips"),
            font=ctk.CTkFont(size=11),
            text_color=("gray60", "gray40"),
            justify="left",
            anchor="nw"
        )
        subtitle_label.pack(anchor="w", pady=(3, 0)) 
        
        # 右侧统计信息
        right_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_frame.pack(side="right", fill="y", padx=15, pady=12)
        
        self.stats_label = ctk.CTkLabel(
            right_frame,
            text="", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            text_color=("#1f6aa5", "#4d9bdb")
        )
        self.stats_label.pack(anchor="e")
        
        # 操作提示
        hint_label = ctk.CTkLabel(
            right_frame,
            text=f"💡 {localization.get('glossary_dialog_edit_tips')}",  # 🔥 简化提示文字
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray60")
        )
        hint_label.pack(anchor="e", pady=(3, 0))
    
    def create_toolbar_section(self, parent):
        """创建工具栏"""
        toolbar_frame = ctk.CTkFrame(parent, height=55, corner_radius=8)  # 🔥 减少高度
        toolbar_frame.pack(fill="x", pady=(0, 12))
        toolbar_frame.pack_propagate(False)
        
        # 编辑按钮组 - 居中布局
        # button_group = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
        # button_group.pack(expand=True, pady=8)
        
        # 添加行
        add_button = ctk.CTkButton(
            toolbar_frame,
            text=f"➕ {localization.get('add_term')}",
            command=self.add_empty_row,
            width=85,    # 🔥 减少宽度
            height=32,   # 🔥 减少高度
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#28a745",
            hover_color="#218838"
        )
        add_button.pack(side="left", padx=(10, 8))
        
        # 删除行
        delete_button = ctk.CTkButton(
            toolbar_frame,
            text=f"🗑️ {localization.get('delete_term')}",
            command=self.delete_selected_rows,
            width=75,    # 🔥 减少宽度
            height=32,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#dc3545",
            hover_color="#c82333"
        )
        delete_button.pack(side="left", padx=8)
        
        # 清空表格
        clear_button = ctk.CTkButton(
            toolbar_frame,
            text=f"🧹 {localization.get('clear_glossary')}",
            command=self.clear_all,
            width=70,
            height=32,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        clear_button.pack(side="left", padx=8)
        
        # AI填充按钮
        smart_button = ctk.CTkButton(
            toolbar_frame,
            text=f"🤖 {localization.get('smart_fill')}",
            command=self.smart_fill_glossary,
            width=85,
            height=32,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#6f42c1",
            hover_color="#5a359a"
        )
        smart_button.pack(side="left", padx=8)
        
        # 导入按钮
        import_button = ctk.CTkButton(
            toolbar_frame,
            text=f"📥 {localization.get('import')}",
            command=self.import_glossary,
            width=70,   # 🔥 增加宽度以容纳文字
            height=32,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#fd7e14",
            hover_color="#e56a07"
        )
        import_button.pack(side="right", padx=(10, 10))
        
        # 导出按钮
        export_button = ctk.CTkButton(
            toolbar_frame,
            text=f"📤 {localization.get('export')}",
            command=self.export_glossary,
            width=70,   # 🔥 增加宽度以容纳文字
            height=32,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#fd7e14",
            hover_color="#e56a07"
        )
        export_button.pack(side="right")
    
    def create_table_section(self, parent):
        """创建表格区域"""
        # 表格容器
        table_container = ctk.CTkFrame(parent, corner_radius=10)
        table_container.pack(fill="both", expand=True, pady=(0, 15))
        
        # 🎯 使用标准 Frame 包装 tksheet
        sheet_frame = tk.Frame(table_container, bg="#212121")
        sheet_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 🔥 创建 tksheet 表格
        self.sheet = Sheet(
            sheet_frame,
            # 🎨 外观配置
            theme="dark blue",                    # 深色主题
            outline_thickness=2,                  # 边框厚度
            outline_color="#1f6aa5",             # 边框颜色
            
            # 🎨 表头配置
            header_bg="#1f6aa5",                 # 表头背景色
            header_fg="white",                   # 表头文字色
            header_font=("Arial", 18, "bold"), # 表头字体
            header_height=50,                    # 表头高度
            
            # 🎨 行配置
            index_bg="#404040",                  # 行号背景
            index_fg="white",                    # 行号文字
            index_font=("Arial", 18, "normal"),        # 行号字体
            index_width=50,                      # 行号宽度
            
            row_height=50,                     # 行高
            column_width=350,                # 列宽
            
            # 🎨 单元格配置
            table_bg="#2d2d2d",                 # 表格背景
            table_fg="white",                   # 表格文字
            table_font=("Arial", 18, "normal"),        # 表格字体
            
            # 🎨 选中状态
            table_selected_cells_bg="#0078d4",  # 选中单元格背景
            table_selected_cells_fg="white",    # 选中单元格文字
            table_selected_rows_bg="#1a4d73",   # 选中行背景
            table_selected_columns_bg="#1a4d73", # 选中列背景
            
            table_editor_bg="white",          # 编辑器背景
            table_editor_fg="#121212",          # 编辑器文字

            # 🎨 网格线
            table_grid_fg="#404040",            # 网格线颜色
            
            # 🎯 功能配置
            show_table=True,                    # 显示表格
            show_top_left=True,                 # 显示左上角
            show_row_index=True,                # 显示行号
            show_header=True,                   # 显示表头
            show_x_scrollbar=True,              # 显示水平滚动条
            show_y_scrollbar=True,              # 显示垂直滚动条
            
            # 🎯 编辑配置
            edit_cell_validation=True,          # 单元格验证
            startup_select=(0, 0, "cells"),     # 启动选择
            
            # 🎯 默认尺寸
            height=400,
            width=600
        )
        
        # 🔥 设置列标题
        self.sheet.headers([localization.get("source_term"), localization.get("target_term")])

        # # 🔥 设置列宽
        # self.sheet.default_column_width(480)
        
        # 🔥 启用编辑功能
        self.sheet.enable_bindings([
            "single_select",        # 单选
            "row_select",          # 行选择
            "column_width_resize", # 列宽调整
            "arrowkeys",           # 箭头键
            "right_click_popup_menu", # 右键菜单
            "rc_select",           # 右键选择
            "rc_insert_row",       # 右键插入行
            "rc_delete_row",       # 右键删除行
            "rc_insert_column",    # 右键插入列
            "rc_delete_column",    # 右键删除列
            "copy",                # 复制
            "cut",                 # 剪切
            "paste",               # 粘贴
            "delete",              # 删除
            "select_all",          # 全选
            "edit_cell",           # 编辑单元格
            "undo",                # 撤销
            "tab",                 # Tab键
            "up",                  # 上箭头
            "down",                # 下箭头
            "left",                # 左箭头
            "right",               # 右箭头
            "prior",               # Page Up
            "next",                # Page Down
            "end",                 # End键
            "home",                # Home键
        ])
        
        # 🔥 绑定数据变化事件
        self.sheet.bind("<<SheetModified>>", self.on_sheet_modified)
        self.sheet.bind("<<SheetSelect>>", self.on_sheet_select)
        
        # 打包显示
        self.sheet.pack(fill="both", expand=True)
        
        # 进度条
        self.progress_var = ctk.StringVar(value=localization.get("ready"))
        progress_label = ctk.CTkLabel(table_container, textvariable=self.progress_var)
        progress_label.pack(pady=(0, 5))

        self.progress_bar = ctk.CTkProgressBar(table_container)
        self.progress_bar.pack(fill="x", padx=10, pady=(0, 15))
        self.progress_bar.set(0)  # 初始状态
    
    def create_button_section(self, parent):
        """创建底部按钮区域"""
        button_frame = ctk.CTkFrame(parent, fg_color="transparent")
        button_frame.pack(fill="x")
        
        # 右侧按钮
        button_right_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        button_right_frame.pack(side="right", pady=10)
        
        # 取消按钮
        cancel_button = ctk.CTkButton(
            button_right_frame,
            text=f"❌ {localization.get('cancel')}",
            command=self.on_close,
            width=100,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        cancel_button.pack(side="right", padx=(10, 0))
        
        # 保存按钮
        self.save_button = ctk.CTkButton(
            button_right_frame,
            text=f"💾 {localization.get('save')}",
            command=self.save_glossary,
            width=100,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#007bff",
            hover_color="#0056b3"
        )
        self.save_button.pack(side="right")
    
    def load_data(self):
        """加载术语数据到表格"""
        # 清空现有数据
        self.sheet.set_sheet_data([[]])
        
        # 准备数据
        data = []
        for source_term, target_term in self.glossary_data.items():
            data.append([source_term, target_term])
        
        # 如果数据少于10行，添加空行
        if len(data) < 10:
            for _ in range(10 - len(data)):
                data.append(["", ""])

        # 设置数据到表格
        if data:
            self.sheet.set_sheet_data(data)
        
        # 设置焦点到第一个单元格
        self.sheet.see(0, 0)
        self.sheet.select_cell(0, 0)
        
        # 更新统计
        self.update_stats()
        self.update_save_status(False)
    
    def on_sheet_modified(self, event=None):
        """表格数据修改事件"""
        self.has_changes = True
        self.update_data_from_sheet()
        self.update_stats()
        self.update_save_status(True)
    
    def on_sheet_select(self, event=None):
        """表格选择事件"""
        # 可以在这里添加选择相关的逻辑
        pass
    
    def update_data_from_sheet(self):
        """从表格更新内部数据"""
        # 🔥 获取表格所有数据
        sheet_data = self.sheet.get_sheet_data()
        
        # 🔥 清空原数据
        self.glossary_data.clear()
        
        # 🔥 处理表格数据
        for row in sheet_data:
            if len(row) >= 2:
                source = str(row[0]).strip() if row[0] is not None else ""
                target = str(row[1]).strip() if row[1] is not None else ""
                
                # 只保存非空的术语对
                if source and target:
                    self.glossary_data[source] = target

    def process_queue(self):
        """处理任务队列"""
        try:
            while not self.message_queue.empty():
                message = self.message_queue.get()
                value = message.get('value', 0)
                log_message = message.get('log_message', "")
                self.progress_bar.set(value)
                
                if log_message is not None and log_message.strip() != "":
                    self.progress_var.set(log_message)
                    logger.info(log_message)
                    
                if value >= 1.0:
                    self.progress_bar.stop()
                    self.progress_var.set(localization.get("completed"))
                    
                
        except queue.Empty:
            pass
        finally:
            # 继续处理队列
            self.after(100, self.process_queue)

    def update_progress(self, log_message, value):
        """更新进度条"""
        self.message_queue.put({'value': value, 'log_message': log_message})
    
    def update_stats(self):
        """更新术语统计"""
        valid_terms = len(self.glossary_data)
        self.stats_label.configure(text= localization.get("glossary_count").format(count=valid_terms))

    def update_save_status(self, has_changes):
        """更新保存状态"""
        if has_changes:
            self.save_button.configure(
                text=f"💾 {localization.get('save')}*",
                fg_color="#28a745",
                hover_color="#218838"
            )
        else:
            self.save_button.configure(
                text=f"💾 {localization.get('save')}",
                fg_color="#007bff",
                hover_color="#0056b3"
            )
    
    def add_empty_row(self):
        """添加空行"""
        current_data = self.sheet.get_sheet_data()
        current_data.append(["", ""])
        self.sheet.set_sheet_data(current_data)
        
        # 跳转到新行
        new_row = len(current_data) - 1
        self.sheet.see(new_row, 0)
        self.sheet.select_cell(new_row, 0)
    
    def insert_row(self):
        """在当前位置插入行"""
        selected = self.sheet.get_selected_cells()
        if selected:
            row = selected[0][0]
            self.sheet.insert_row(row, ["", ""])
            self.sheet.select_cell(row, 0)
        else:
            self.add_empty_row()
    
    def delete_selected_rows(self):
        """删除选中的行"""
        selected_rows = self.sheet.get_selected_rows()
        if not selected_rows:
            messagebox.showwarning("警告", "请选择要删除的行")
            return
        
        if messagebox.askyesno("确认删除", f"确定要删除选中的 {len(selected_rows)} 行吗？\n此操作不可撤销。"):
            # 从后往前删除，避免索引变化
            for row in sorted(selected_rows, reverse=True):
                self.sheet.delete_row(row)
            
            self.has_changes = True
            self.update_data_from_sheet()
            self.update_stats()
            self.update_save_status(True)
    
    def clear_all(self):
        """清空所有数据"""
        if messagebox.askyesno("确认清空", "⚠️ 确定要清空整个术语表吗？\n此操作不可撤销！"):
            self.sheet.set_sheet_data([[]])
            self.glossary_data.clear()
            self.has_changes = True
            self.update_stats()
            self.update_save_status(True)
    
    def smart_fill_glossary(self):
        """AI智能填充术语表"""
        if self.glossary_data:
            if not messagebox.askyesno(
                "确认填充",
                "⚠️ 术语表已包含数据，继续将覆盖现有内容。\n\n"
                "是否继续进行AI智能填充？"
            ):
                return
        
        self.progress_bar.configure(mode="determinate")
        # self.progress_bar.start()
        self.progress_var.set(localization.get("processing"))
        
        self.process_thread = threading.Thread(
            target=self.process_fill_glossary,
            daemon=True
        )
        self.process_thread.start()
        
    def process_fill_glossary(self):
        """处理AI智能填充术语表"""
        try:
            self.stop_event.clear()
            
            # 调用生成术语表的函数
            args = {
                'input': self.input_path,
                'target_language': self.target_lang,
                'model_path': self.model_path,
                'n_gpu_layers': self.n_gpu_layers,
                'stop_event': self.stop_event,
                'update_progress': self.update_progress
            }
            
            glossary_data = generate_glossary(args)
            if glossary_data is not None and len(glossary_data) > 0:
                self.glossary_data = glossary_data
                
                # 重新加载数据到表格
                self.load_data()
                
                # 更新状态
                self.has_changes = True
                self.update_stats()
                self.update_save_status(True)
                self.progress_var.set(localization.get("completed"))
            
            
        except Exception as e:
            messagebox.showerror("智能填充失败", f"❌ 智能填充过程中发生错误：\n\n{str(e)}")
    
    def import_glossary(self):
        """导入术语表"""
        from tkinter import filedialog
        filename = filedialog.askopenfilename(
            title= localization.get("import_glossary"),
            filetypes=[("CSV文件", "*.csv")]
        )
        
        if filename:
            try:
                imported_count = 0
                imported_data = []
                            
                if filename.endswith('.csv'):
                    import csv
                    with open(filename, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        # 跳过可能的标题行
                        first_row = next(reader, None)
                        if first_row and ('术语' in str(first_row) or 'term' in str(first_row).lower()):
                            pass  # 跳过标题行
                        else:
                            if first_row and len(first_row) >= 2:
                                imported_data.append([first_row[0].strip(), first_row[1].strip()])
                                imported_count += 1
                        
                        for row in reader:
                            if len(row) >= 2 and row[0].strip() and row[1].strip():
                                imported_data.append([row[0].strip(), row[1].strip()])
                                imported_count += 1
                        
                else:
                    messagebox.showerror("格式错误", "❌ 不支持的文件格式\n\n支持的格式：JSON、CSV、Excel")
                    return
                
                if imported_data:
                    # 询问是否替换现有数据
                    if self.glossary_data:
                        choice = messagebox.askyesnocancel(
                            localization.get("import_glossary"),
                            localization.get("import_glossary_tips").format(
                                glossary_count=len(self.glossary_data),
                                imported_count=imported_count
                            )
                        )
                        if choice is None:  # 取消
                            return
                        elif choice is False:  # 替换
                            self.sheet.set_sheet_data(imported_data)
                        else:  # 合并
                            current_data = self.sheet.get_sheet_data()
                            # 过滤掉空行
                            current_data = [row for row in current_data if len(row) >= 2 and any(str(cell).strip() for cell in row[:2])]
                            # 添加导入的数据
                            current_data.extend(imported_data)
                            self.sheet.set_sheet_data(current_data)
                    else:
                        self.sheet.set_sheet_data(imported_data)
                    
                    # 添加一些空行
                    current_data = self.sheet.get_sheet_data()
                    for _ in range(5):
                        current_data.append(["", ""])
                    self.sheet.set_sheet_data(current_data)
                    
                    # 更新数据
                    self.has_changes = True
                    self.update_data_from_sheet()
                    self.update_stats()
                    self.update_save_status(True)
                else:
                    messagebox.showwarning("导入警告", "⚠️ 文件中没有找到有效的术语数据")
                    
            except Exception as e:
                messagebox.showerror("导入失败", f"❌ 导入过程中发生错误：\n\n{str(e)}")
    
    def export_glossary(self):
        """导出术语表"""
        from tkinter import filedialog
        
        # 更新数据
        self.update_data_from_sheet()
        
        if not self.glossary_data:
            messagebox.showwarning("导出警告", "⚠️ 术语表为空，无法导出")
            return
        
        filename = filedialog.asksaveasfilename(
            title=localization.get("export_glossary"),
            defaultextension=".json",
            filetypes=[
                ("CSV文件", "*.csv"), 
            ]
        )
        
        if filename:
            try:
                if filename.endswith('.csv'):
                    import csv
                    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:  # 使用BOM避免乱码
                        writer = csv.writer(f)
                        writer.writerow(['Source Term', 'Target Term'])
                        for source, target in self.glossary_data.items():
                            writer.writerow([source, target])
                
                messagebox.showinfo(
                    localization.get("export_glossary_success"), 
                    localization.get("export_glossary_success_tips").format(
                        filename=filename,
                        glossary_count=len(self.glossary_data)
                    )
                )
                
            except Exception as e:
                messagebox.showerror("导出失败", f"❌ 导出过程中发生错误：\n\n{str(e)}")
    
    def save_glossary(self):
        """保存术语表"""
        try:
            # 更新数据
            self.update_data_from_sheet()
            
            # 更新全局术语表
            glossary.glossary = self.glossary_data.copy()
            glossary.save_glossary(glossary.to_glossary_filename(self.filename))
            
            self.has_changes = False
            self.update_save_status(False)
            
            # 显示保存成功消息
            # messagebox.showinfo(
            #     "保存成功", 
            #     f"✅ 术语表保存成功！\n\n"
            #     f"📊 有效术语: {len(self.glossary_data)} 个\n"
            #     f"💡 术语表将自动应用到翻译过程中"
            # )
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("保存失败", f"❌ 保存过程中发生错误：\n\n{str(e)}")
    
    def on_close(self):
        """关闭对话框"""
        if self.process_thread and self.process_thread.is_alive():
            result = messagebox.askokcancel(
                localization.get("smart_fill_processing"),
                localization.get("smart_fill_processing_tips")
            )
            if result:
                self.stop_event.set()
                self.progress_var.set(localization.get("stopped"))
                self.progress_bar.stop()
            else:
                return
            
            self.process_thread.join()
            self.process_thread = None
            
        if self.has_changes:
            result = messagebox.askyesnocancel(
                localization.get("unsaved_changes"),
                localization.get("unsaved_changes_tips")
            )
            if result is True:  # 保存
                self.save_glossary()
                return
            elif result is None:  # 取消
                return
            # False = 不保存，直接关闭
        
        self.destroy()