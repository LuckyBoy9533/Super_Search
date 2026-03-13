# src/ui/main_window.py
import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any
from win32com.shell import shell, shellcon

# 导入配置和引擎
from config import FILE_CATEGORIES, UI_DISPLAY_LIMIT, ICON_FILENAME
from core.engine import SearchEngine
from core.recycle_bin import RecycleBinManager

# 导入UI和工具
from .tray_icon import TrayManager
from utils.helpers import format_size, get_resource_path
from utils.icons import IconManager

# 【改造】导入国际化和设置模块
from .locales import get_text, set_language, LANGUAGE_NAMES, current_lang
from utils.settings import save_settings


class MainWindow:
    """应用程序主界面 (View/Controller)"""

    def __init__(self, root: tk.Tk, engine: SearchEngine, settings: dict):
        self.root = root
        self.engine = engine
        self.settings = settings  # 【新增】保存设置

        # 【改造】从 settings.json 初始化语言
        initial_lang = self.settings.get("language", "zh")
        set_language(initial_lang)

        self.sort_col = None
        self.sort_reverse = False
        self._search_timer = None

        self.tray_manager = TrayManager(self, self.root)

        # 注册引擎回调
        self.engine.on_scan_progress = self.update_scan_progress
        self.engine.on_scan_complete = self.on_scan_complete
        self.engine.on_data_updated = self.refresh_ui
        self.engine.on_status_msg = self.show_status_msg

        # 初始化图标与UI
        self.icon_manager = IconManager()
        self.setup_ui()  # 先绘制UI，此时无文本
        self.retranslate_ui()  # 再填充所有文本
        self.setup_context_menu()
        self.bind_events()

        # 初始化加载逻辑
        self.show_status_msg(get_text("waking_cache_status"), "orange")
        self.root.update()

        if self.engine.load_cache():
            total = len(self.engine.file_index_dict)
            self.show_status_msg(get_text("instant_finish_status", total=total), "green")
            self.trigger_search()
        else:
            self.engine.start_fast_indexing()

    def setup_ui(self):
        """初始化UI布局（无文本）"""
        self._set_window_icon()
        self.root.geometry("1000x650")

        top_frame = tk.Frame(self.root, pady=10, padx=10)
        top_frame.pack(fill=tk.X)

        self.search_label = tk.Label(top_frame)
        self.search_label.pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(top_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=10)

        self.filter_label = tk.Label(top_frame)
        self.filter_label.pack(side=tk.LEFT, padx=(20, 5))
        self.filter_var = tk.StringVar()
        self.filter_combo = ttk.Combobox(top_frame, textvariable=self.filter_var, state="readonly", width=12)
        self.filter_combo.pack(side=tk.LEFT)

        # 【改造】语言切换下拉框
        self.lang_label = tk.Label(top_frame)
        self.lang_label.pack(side=tk.LEFT, padx=(20, 5))
        self.lang_var = tk.StringVar()
        self.lang_combo = ttk.Combobox(top_frame, textvariable=self.lang_var, state="readonly", width=12)
        self.lang_combo.pack(side=tk.LEFT)

        self.status_label = tk.Label(top_frame, fg="blue")
        self.status_label.pack(side=tk.RIGHT)

        mid_frame = tk.Frame(self.root, padx=10, pady=5)
        mid_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("filename", "filepath", "size", "mtime", "is_deleted", "real_path")
        self.tree = ttk.Treeview(mid_frame, columns=columns, show="tree headings",
                                 displaycolumns=("filename", "filepath", "size", "mtime"))
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(mid_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def retranslate_ui(self):
        """【核心改造】应用当前语言的文本，并保持下拉框选择"""
        # 1. 在更新前，记录当前两个下拉框的选中项索引
        current_filter_index = self.filter_combo.current()
        current_lang_index = self.lang_combo.current()

        # 2. 更新所有静态文本
        self.root.title(get_text("title"))
        self.search_label.config(text=get_text("search_label"))
        self.filter_label.config(text=get_text("filter_label"))
        self.lang_label.config(text=get_text("language_label"))
        self.status_label.config(text=get_text("ready_status"))

        # 3. 更新筛选器下拉框 (Filter Combobox)
        #    从 config 中获取中立的 key，然后用 get_text 翻译它们
        translated_categories = [get_text(k) for k in FILE_CATEGORIES.keys()]
        self.filter_combo["values"] = translated_categories
        if current_filter_index != -1:
            self.filter_combo.current(current_filter_index)
        else: # 程序首次加载时，默认为第一个选项
            self.filter_combo.current(0)

        # 4. 更新语言下拉框 (Language Combobox)
        self.lang_combo["values"] = list(LANGUAGE_NAMES.values())
        # 如果已有选择，则保持；否则根据当前语言代码设置
        if current_lang_index != -1:
            self.lang_combo.current(current_lang_index)
        else:
            lang_index = list(LANGUAGE_NAMES.keys()).index(current_lang)
            self.lang_combo.current(lang_index)

        # 5. 更新列表表头
        self.tree.column("#0", width=40, stretch=False, anchor=tk.CENTER)
        self.tree.heading("#0", text=get_text("tree_col_icon"))
        self._update_heading_arrows()  # 更新表头文本和排序箭头

    def switch_language(self, event=None):
        """【核心改造】切换语言，保存设置，并刷新整个UI"""
        selected_lang_name = self.lang_var.get()
        # 反向查找语言代码 (e.g., "简体中文" -> "zh")
        lang_code = next((code for code, name in LANGUAGE_NAMES.items() if name == selected_lang_name), None)

        if lang_code and lang_code != self.settings.get("language"):
            # 更新全局语言状态
            set_language(lang_code)
            # 更新并保存设置
            self.settings["language"] = lang_code
            save_settings(self.settings)
            # 重新翻译整个UI
            self.retranslate_ui()
            # 触发一次搜索，以刷新可能包含语言文本的状态栏消息
            self.trigger_search()

    def setup_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)

    def bind_events(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.search_var.trace_add("write", lambda *args: self.trigger_search())
        self.filter_combo.bind("<<ComboboxSelected>>", self.trigger_search)
        self.lang_combo.bind("<<ComboboxSelected>>", self.switch_language)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def _set_window_icon(self):
        """【修复】确保使用正确的图标文件名常量"""
        # 确保你已经从 utils.helpers 导入了 get_resource_path
        icon_path = get_resource_path("assets/app_icon.ico")
        try:
            self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"图标加载失败: {e}")

    def update_scan_progress(self, count: int, current_dir: str):
        msg = get_text("scan_progress_status", count=count, current_dir=current_dir)
        self.root.after(0, lambda: self.show_status_msg(msg, "red"))

    def on_scan_complete(self, total_count: int):
        msg = get_text("scan_complete_status", total_count=total_count)
        self.root.after(0, lambda: self.show_status_msg(msg, "green"))
        self.root.after(0, self.trigger_search)

    def show_status_msg(self, msg: str, color: str):
        self.root.after(0, lambda: self.status_label.config(text=msg, fg=color))

    def refresh_ui(self):
        self.root.after(0, self.trigger_search)

    def trigger_search(self, event=None):
        if self._search_timer:
            self.root.after_cancel(self._search_timer)
        self._search_timer = self.root.after(250, self._do_search)

    def _do_search(self):
        keyword = self.search_var.get()

        # 【核心改造】通过索引获取中立的 category key，而不是通过翻译后的字符串
        selected_filter_index = self.filter_combo.current()
        if selected_filter_index == -1: # 如果没有选中项，默认为 'all'
            selected_filter_index = 0
        category_key = list(FILE_CATEGORIES.keys())[selected_filter_index]

        results, match_count = self.engine.perform_search(keyword, category_key, self.sort_col, self.sort_reverse)

        if match_count == -1:
            self.root.after(50, self._do_search)
            return

        self.render_treeview(results)
        self._update_heading_arrows()

        if not keyword and category_key == "category_all":
            total = len(self.engine.file_index_dict)
            self.show_status_msg(get_text("instant_finish_status", total=total), "green")
        else:
            limit_tip = f" (Top {UI_DISPLAY_LIMIT})" if match_count > UI_DISPLAY_LIMIT else ""
            self.show_status_msg(get_text("found_objects_status", match_count=match_count, limit_tip=limit_tip), "green")

    def render_treeview(self, results):
        self.tree.delete(*self.tree.get_children())
        import datetime
        for _, orig_name, _, path, icon_key, size, mtime, is_deleted, real_path in results:
            icon = self.icon_manager.get_icon(icon_key)
            display_size = format_size(size) if size != -1 else ""
            try:
                display_time = datetime.datetime.fromtimestamp(mtime).strftime('%Y/%m/%d %H:%M')
            except:
                display_time = get_text("unknown_time")

            self.tree.insert("", tk.END, text="", image=icon,
                             values=(orig_name, path, display_size, display_time, is_deleted, real_path))

    def sort_treeview(self, col):
        if self.sort_col == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_col = col
            self.sort_reverse = False
        self.trigger_search()

    def _update_heading_arrows(self):
        headings = {
            "filename": "tree_col_name",
            "filepath": "tree_col_path",
            "size": "tree_col_size",
            "mtime": "tree_col_mtime"
        }
        for col, text_key in headings.items():
            # 先获取翻译后的文本
            translated_text = get_text(text_key)
            # 再添加排序箭头
            arrow = " ▼" if self.sort_reverse and self.sort_col == col else " ▲" if self.sort_col == col else ""
            self.tree.heading(col, text=translated_text + arrow, command=lambda c=col: self.sort_treeview(c))
            # 为 TreeView 列设置固定的宽度和对齐方式
            if text_key == "tree_col_name": self.tree.column(col, width=250, anchor=tk.W)
            elif text_key == "tree_col_path": self.tree.column(col, width=400, stretch=True, anchor=tk.W)
            elif text_key == "tree_col_size": self.tree.column(col, width=80, anchor=tk.E)
            elif text_key == "tree_col_mtime": self.tree.column(col, width=120, anchor=tk.W)

    def show_context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid: return

        selected_items = self.tree.selection()
        if iid not in selected_items:
            self.tree.selection_set(iid)
            selected_items = [iid]

        is_deleted = (str(self.tree.item(iid, "values")[4]) == 'True')
        count = len(selected_items)
        self.context_menu.delete(0, tk.END)

        if is_deleted:
            self.context_menu.add_command(label=get_text("restore_action", count=count), command=self.action_restore)
            if count == 1:
                self.context_menu.add_command(label=get_text("restore_and_open_action"), command=self.action_restore_and_open)
            self.context_menu.add_separator()
            self.context_menu.add_command(label=get_text("permanently_delete_action", count=count), command=self.action_permanently_delete)
            self.context_menu.add_command(label=get_text("empty_recycle_bin_action"), command=self.action_empty_recycle_bin)
        else:
            if count == 1:
                self.context_menu.add_command(label=get_text("open_file_action"), command=self.action_open_file)
                self.context_menu.add_command(label=get_text("open_folder_action"), command=self.action_open_folder)
                self.context_menu.add_command(label=get_text("copy_path_action"), command=self.action_copy_path)
            self.context_menu.add_separator()
            self.context_menu.add_command(label=get_text("move_to_recycle_bin_action", count=count), command=self.action_move_to_recycle_bin)

        self.context_menu.tk_popup(event.x_root, event.y_root)

    def on_double_click(self, event):
        selected = self.tree.selection()
        if not selected: return
        is_deleted = (str(self.tree.item(selected[0], "values")[4]) == 'True')
        if is_deleted:
            self.action_restore_and_open()
        else:
            self.action_open_file()

    def get_selected_items_data(self):
        return [(self.tree.item(item, "values")[1], self.tree.item(item, "values")[5]) for item in self.tree.selection()]

    def action_copy_path(self):
        data = self.get_selected_items_data()
        paths = "\n".join(d[0] for d in data)
        self.root.clipboard_clear()
        self.root.clipboard_append(paths)
        self.root.update()
        self.show_status_msg(get_text("path_copied_status"), "green")

    def action_open_file(self):
        data = self.get_selected_items_data()
        if data and os.path.exists(data[0][1]):
            try:
                os.startfile(data[0][1])
            except Exception:
                pass

    def action_open_folder(self):
        data = self.get_selected_items_data()
        if data and os.path.exists(data[0][1]):
            try:
                subprocess.run(['explorer', '/select,', os.path.normpath(data[0][1])])
            except Exception:
                pass

    def action_move_to_recycle_bin(self):
        data = self.get_selected_items_data()
        real_paths = [d[1] for d in data]
        if not messagebox.askyesno(get_text("move_to_recycle_bin_confirm", count=len(real_paths))):
            return

        success_count = 0
        try:
            flags = shellcon.FOF_ALLOWUNDO | shellcon.FOF_NOCONFIRMATION | shellcon.FOF_SILENT | shellcon.FOF_NOERRORUI
            for path in real_paths:
                if os.path.exists(path):
                    res, aborted = shell.SHFileOperation((0, shellcon.FO_DELETE, path, None, flags, None, None))
                    if res == 0 and not aborted:
                        success_count += 1
                        self.engine.file_index_dict.pop(path.lower(), None)
        except Exception as e:
            messagebox.showerror(get_text("error_title"), str(e))

        if success_count > 0:
            self.engine.trigger_recycle_bin_refresh()
        self.trigger_search()

    def action_restore(self) -> bool:
        data = self.get_selected_items_data()
        real_paths = [d[1] for d in data]
        display_paths = [d[0] for d in data]

        if RecycleBinManager.restore_files(real_paths):
            for p in display_paths:
                self.engine.sync_index_hot_reload(p, "created")
            return True
        return False

    def action_restore_and_open(self):
        data = self.get_selected_items_data()
        if not data: return
        display_paths = [d[0] for d in data]

        if self.action_restore() and os.path.exists(display_paths[0]):
            try:
                os.startfile(display_paths[0])
            except Exception:
                pass

    def action_permanently_delete(self):
        data = self.get_selected_items_data()
        real_paths = [d[1] for d in data]
        warn_msg = get_text("permanently_delete_warning", count=len(real_paths))
        if not messagebox.askyesno(get_text("error_title"), warn_msg):
            return

        if RecycleBinManager.permanently_delete(real_paths):
            for p in real_paths:
                self.engine.file_index_dict.pop(p.lower(), None)
            self.trigger_search()

    def action_empty_recycle_bin(self):
        if not messagebox.askyesno(get_text("error_title"), get_text("empty_recycle_bin_warning")):
            return

        try:
            RecycleBinManager.empty_bin()
            keys_to_delete = [k for k, v in self.engine.file_index_dict.items() if v[7]]
            for k in keys_to_delete:
                del self.engine.file_index_dict[k]
            self.trigger_search()
            messagebox.showinfo(get_text("title"), get_text("empty_recycle_bin_success"))
        except Exception as e:
            messagebox.showerror(get_text("error_title"), str(e))

    def on_closing(self):
        response = messagebox.askyesnocancel(
            get_text("exit_prompt_title"),
            get_text("exit_prompt_message")
        )
        if response is True:
            self.full_quit()
        elif response is False:
            self.tray_manager.hide_to_tray()

    def full_quit(self):
        self.show_status_msg(get_text("saving_snapshot_status"), "red")
        self.root.update()
        self.engine.save_cache()
        self.tray_manager.stop()
        self.root.destroy()