# src/ui/main_window.py
import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any
from win32com.shell import shell, shellcon

from config import FILE_CATEGORIES
from core.recycle_bin import RecycleBinManager
from .tray_icon import TrayManager

# 预引入下一步要写的工具库
from utils.helpers import format_size, get_resource_path
from config import ICON_FILENAME
from utils.icons import IconManager


class MainWindow:
    """应用程序主界面 (View/Controller)"""

    def __init__(self, root: tk.Tk, engine: Any):
        self.root = root
        self.engine = engine

        self.root.title("Super Search")
        self.root.geometry("1000x650")

        self.sort_col = None
        self.sort_reverse = False
        self._search_timer = None

        # 托盘管理器初始化
        self.tray_manager = TrayManager(self.root, self.full_quit)

        # 注册引擎回调插槽（依赖注入的威力）
        self.engine.on_scan_progress = self.update_scan_progress
        self.engine.on_scan_complete = self.on_scan_complete
        self.engine.on_data_updated = self.refresh_ui
        self.engine.on_status_msg = self.show_status_msg

        # 初始化图标与UI
        self.icon_manager = IconManager()
        self._set_window_icon()
        self.setup_ui()
        self.setup_context_menu()
        self.bind_events()

        # 初始化加载逻辑
        self.status_label.config(text="正在唤醒缓存...", fg="orange")
        self.root.update()

        if self.engine.load_cache():
            total = len(self.engine.file_index_dict)
            self.status_label.config(text=f"秒开完成！已加载 {total} 个历史项目", fg="green")
            self.trigger_search()
        else:
            self.engine.start_fast_indexing()

    def _set_window_icon(self):
        try:
            self.root.iconbitmap(get_resource_path(ICON_FILENAME))
        except Exception:
            pass

    def setup_ui(self):
        """纯粹的 UI 绘制代码"""
        top_frame = tk.Frame(self.root, pady=10, padx=10)
        top_frame.pack(fill=tk.X)

        tk.Label(top_frame, text="搜索文件名:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(top_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=10)

        tk.Label(top_frame, text="  筛选:").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar(value="所有")
        self.filter_combo = ttk.Combobox(
            top_frame, textvariable=self.filter_var,
            values=list(FILE_CATEGORIES.keys()), state="readonly", width=12
        )
        self.filter_combo.pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(top_frame, text="准备就绪", fg="blue")
        self.status_label.pack(side=tk.RIGHT)

        mid_frame = tk.Frame(self.root, padx=10, pady=5)
        mid_frame.pack(fill=tk.BOTH, expand=True)

        # 【核心修改】：新增 real_path 列，但保证 displaycolumns 不包含它，实现隐藏存储
        columns = ("filename", "filepath", "size", "mtime", "is_deleted", "real_path")
        self.tree = ttk.Treeview(mid_frame, columns=columns, show="tree headings",
                                 displaycolumns=("filename", "filepath", "size", "mtime"))

        self.tree.column("#0", width=40, stretch=False, anchor=tk.CENTER)
        self.tree.heading("#0", text="图标")

        for col, text, width, anchor in [
            ("filename", "名称", 250, tk.W),
            ("filepath", "路径", 400, tk.W),
            ("size", "大小", 80, tk.E),
            ("mtime", "修改时间", 120, tk.W)
        ]:
            self.tree.heading(col, text=text, anchor=anchor, command=lambda c=col: self.sort_treeview(c))
            self.tree.column(col, width=width, stretch=(col == "filepath"), anchor=anchor)

        scrollbar = ttk.Scrollbar(mid_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)

    def bind_events(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.search_var.trace_add("write", lambda *args: self.trigger_search())
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self.trigger_search())
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

    # --- 引擎回调更新界面 ---
    def update_scan_progress(self, count: int, current_dir: str):
        # 必须用 self.root.after 确保在主线程更新 UI
        self.root.after(0, lambda: self.status_label.config(
            text=f"扫描中 ({count} 项) ... 当前: {current_dir[:30]}", fg="red"
        ))

    def on_scan_complete(self, total_count: int):
        self.root.after(0, lambda: self.status_label.config(
            text=f"加载完成！共 {total_count} 个项目", fg="green"
        ))
        self.root.after(0, self.trigger_search)

    def show_status_msg(self, msg: str, color: str):
        self.root.after(0, lambda: self.status_label.config(text=msg, fg=color))

    def refresh_ui(self):
        self.root.after(0, self.trigger_search)

    # --- 搜索与渲染逻辑 ---
    def trigger_search(self):
        """UI防抖控制"""
        if self._search_timer:
            self.root.after_cancel(self._search_timer)
        self._search_timer = self.root.after(300, self._do_search)

    def _do_search(self):
        keyword = self.search_var.get()
        current_filter = self.filter_var.get()

        # 调用核心大脑获取数据
        results, match_count = self.engine.perform_search(keyword, current_filter, self.sort_col, self.sort_reverse)

        if match_count == -1:
            # 引擎正在后台写数据被锁，延迟重试
            self.root.after(50, self._do_search)
            return

        self.render_treeview(results)
        self._update_heading_arrows()

        # 状态栏文字更新
        if not keyword and current_filter == "所有":
            total = len(self.engine.file_index_dict)
            self.status_label.config(text=f"秒开完成！共 {total} 个项目", fg="green")
        else:
            limit_tip = " (列表仅展示前1000项)" if match_count > 1000 else ""
            self.status_label.config(text=f"找到 {match_count} 个对象{limit_tip}", fg="green")

    def render_treeview(self, results):
        self.tree.delete(*self.tree.get_children())
        import datetime
        for _, orig_name, _, path, icon_key, size, mtime, is_deleted, real_path in results:
            icon = self.icon_manager.get_icon(icon_key)
            display_size = format_size(size) if size != -1 else ""
            try:
                display_time = datetime.datetime.fromtimestamp(mtime).strftime('%Y/%m/%d %H:%M')
            except:
                display_time = "未知"

            # 【核心修改】：将 real_path 一同存入 values 中
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
        headings = {"filename": "名称", "filepath": "路径", "size": "大小", "mtime": "修改时间"}
        for col, text in headings.items():
            arrow = " ▼" if self.sort_reverse else " ▲" if col == self.sort_col else ""
            self.tree.heading(col, text=text + arrow)

    # --- 右键菜单与业务动作 ---
    def show_context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid: return

        selected_items = self.tree.selection()
        if iid not in selected_items:
            self.tree.selection_set(iid)
            selected_items = [iid]

        is_deleted = (str(self.tree.item(iid, "values")[4]) == 'True')
        self.context_menu.delete(0, tk.END)

        if is_deleted:
            self.context_menu.add_command(label=f"♻️ 还原选中的 {len(selected_items)} 个文件",
                                          command=self.action_restore)
            if len(selected_items) == 1:
                self.context_menu.add_command(label="📂 还原并打开此文件", command=self.action_restore_and_open)
            self.context_menu.add_separator()
            self.context_menu.add_command(label=f"❌ 彻底删除选定的 {len(selected_items)} 个项目",
                                          command=self.action_permanently_delete)
            self.context_menu.add_command(label="🗑️ 清空整个回收站", command=self.action_empty_recycle_bin)
        else:
            if len(selected_items) == 1:
                self.context_menu.add_command(label="打开 (文件/文件夹)", command=self.action_open_file)
                self.context_menu.add_command(label="打开所在位置 (并选中)", command=self.action_open_folder)
                self.context_menu.add_command(label="📋 复制文件路径", command=self.action_copy_path)
            self.context_menu.add_separator()
            self.context_menu.add_command(label=f"🗑️ 移动到回收站 ({len(selected_items)} 项)",
                                          command=self.action_move_to_recycle_bin)

        self.context_menu.tk_popup(event.x_root, event.y_root)

    def on_double_click(self, event):
        selected = self.tree.selection()
        if not selected: return
        is_deleted = (str(self.tree.item(selected[0], "values")[4]) == 'True')
        if is_deleted:
            self.action_restore_and_open()
        else:
            self.action_open_file()

    # --- 具体交互实现 ---
    def get_selected_paths(self):
        return [self.tree.item(item, "values")[1] for item in self.tree.selection()]

    def get_selected_items_data(self):
        """【新增组件】统一获取选中项的双重信息：[(显示路径, 真实底物理径), ...]"""
        # values[1] 是原路径，values[5] 是隐形的底层真实路径
        return [(self.tree.item(item, "values")[1], self.tree.item(item, "values")[5]) for item in
                self.tree.selection()]

    def action_copy_path(self):
        data = self.get_selected_items_data()
        paths = "\n".join(d[0] for d in data)  # 复制给用户看的显示路径
        self.root.clipboard_clear()
        self.root.clipboard_append(paths)
        self.root.update()
        self.status_label.config(text=f"已复制路径", fg="green")

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
        if not messagebox.askyesno("移至回收站", f"确定要把这 {len(real_paths)} 个项目移到回收站吗？"): return

        success_count = 0
        try:
            for path in real_paths:
                if os.path.exists(path):
                    flags = shellcon.FOF_ALLOWUNDO | shellcon.FOF_NOCONFIRMATION | shellcon.FOF_SILENT | shellcon.FOF_NOERRORUI
                    res, aborted = shell.SHFileOperation((0, shellcon.FO_DELETE, path, None, flags, None, None))
                    if res == 0 and not aborted:
                        success_count += 1
                        self.engine.file_index_dict.pop(path.lower(), None)
        except Exception as e:
            messagebox.showerror("错误", str(e))

        if success_count > 0:
            self.engine.trigger_recycle_bin_refresh()
        self.trigger_search()

    def action_restore(self) -> bool:
        data = self.get_selected_items_data()
        real_paths = [d[1] for d in data]  # 给底层用来精准还原
        display_paths = [d[0] for d in data]  # 给引擎用来更新显示

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
        if not messagebox.askyesno("警告", f"【危险操作】\n确定要彻底粉碎这 {len(real_paths)} 个文件吗？"): return

        if RecycleBinManager.permanently_delete(real_paths):
            for p in real_paths:
                self.engine.file_index_dict.pop(p.lower(), None)
            self.trigger_search()

    def action_empty_recycle_bin(self):
        if not messagebox.askyesno("清空回收站", "【毁灭级操作】\n确定要清空回收站里的所有文件吗？"): return

        try:
            RecycleBinManager.empty_bin()
            keys_to_delete = [k for k, v in self.engine.file_index_dict.items() if v[7]]
            for k in keys_to_delete:
                del self.engine.file_index_dict[k]
            self.trigger_search()
            messagebox.showinfo("完成", "系统回收站已彻底清空！")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    # --- 退出控制 ---
    def on_closing(self):
        response = messagebox.askyesnocancel("退出提示", "点击【是】直接退出\n点击【否】最小化到系统托盘\n点击【取消】返回")
        if response is True:
            self.full_quit()
        elif response is False:
            self.tray_manager.hide_to_tray()

    def full_quit(self):
        self.status_label.config(text="正在保存快照，请稍候...", fg="red")
        self.root.update()
        self.engine.save_cache()
        self.root.destroy()