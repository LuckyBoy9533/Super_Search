# Copyright (c) 2026 [Barry Allen]
# This code is licensed under the GPL 3.0 License.
# For commercial use, please contact: [zhang5626833@gmail.com]

import os
import sys
import pythoncom
import pickle
import win32com.client
from win32com.shell import shell, shellcon
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import platform
import string
import math
from datetime import datetime
import ctypes
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

try:
    import pystray
    from PIL import Image, ImageDraw, ImageTk
except ImportError:
    pass

try:
    myappid = 'my_personal.super_search.version.1.1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass


def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_data_path(filename):
    """专门用于读写持久化数据（如缓存文件），确保它和 exe 放在同一个目录下"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的 exe 运行环境
        base_dir = os.path.dirname(sys.executable)
    else:
        # 如果是 py 脚本运行环境
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, filename)

class SearchFileEventHandler(FileSystemEventHandler):
    """超级哨兵：联动回收站监控"""

    def __init__(self, app_instance):
        self.app = app_instance

    def on_any_event(self, event):
        if event.event_type == 'created':
            self.app.sync_index_hot_reload(event.src_path, "created")
        elif event.event_type == 'deleted':
            self.app.sync_index_hot_reload(event.src_path, "deleted")
        elif event.event_type == 'moved':
            self.app.sync_index_hot_reload(event.src_path, "deleted")
            self.app.sync_index_hot_reload(event.dest_path, "created")

        # 节流机制：避免高频触发回收站扫描
        if hasattr(self.app, '_rb_timer') and self.app._rb_timer:
            self.app.root.after_cancel(self.app._rb_timer)
        self.app._rb_timer = self.app.root.after(1000, self.app.refresh_recycle_bin_only)


class MiniEverything:
    def __init__(self, root):
        self.root = root
        self.root.title("Super Search")
        self.root.geometry("1000x650")

        # 核心优化：使用 Dict 替代 List 实现 O(1) 的超快去重和检索
        # 结构: { "c:\path\to\file": (name_lower, orig_name, ext, path, icon_key, size, mtime, is_deleted) }
        self.file_index_dict = {}
        self.current_results = []
        self.is_indexing = False
        self.sort_col = None
        self.sort_reverse = False
        self._search_timer = None  # 搜索防抖定时器

        self._start_watcher()

        icon_path = get_resource_path("app_icon.ico")
        try:
            self.root.iconbitmap(icon_path)
        except Exception:
            pass

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.file_categories = {
            "所有": set(),
            "音频": {".mp3", ".wav", ".flac"},
            "视频": {".mp4", ".mkv", ".avi", ".mov"},
            "图片": {".png", ".jpg", ".jpeg", ".gif", ".ico"},
            "文档": {".doc", ".docx", ".pdf", ".txt", ".md", ".xlsx"},
            "压缩文件": {".zip", ".rar", ".7z"},
            "代码": {".py", ".java", ".c", ".cpp", ".html", ".css", ".js"},
            "文件夹": {"folder"},
            "🗑️ 回收站": {"recycle_bin"}
        }

        self.init_icons()
        self.setup_ui()
        self.setup_context_menu()
        self.status_label.config(text="正在唤醒缓存...", fg="orange")
        self.root.update()  # 强制刷新一下UI让用户看到字

        if self.load_cache():
            total = len(self.file_index_dict)
            self.status_label.config(text=f"秒开完成！已加载 {total} 个历史项目", fg="green")
            self.perform_search()

            # 后台静默扫描（弥补普通文件的离线变动）
            threading.Thread(target=self._background_silent_sync, daemon=True).start()

            # 👇 --- 资深工程师补丁：强制刷新离线期间的回收站变动 --- 👇
            # 延迟 500 毫秒执行，避免和 UI 渲染抢占主线程资源
            self.root.after(500, self.refresh_recycle_bin_only)
            # 👆 --------------------------------------------------- 👆
        else:
            # 如果是第一次运行，或者缓存文件被删了，才执行全盘扫描
            self.start_fast_indexing()

    def load_cache(self):
        """光速启动：从本地读取快照"""
        cache_path = get_data_path("index_cache.pkl")  # <--- 改用 get_data_path
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    self.file_index_dict = pickle.load(f)
                return True
            except Exception:
                return False
        return False

    def save_cache(self):
        """退出时的收尾工作：保存快照"""
        cache_path = get_data_path("index_cache.pkl")  # <--- 改用 get_data_path
        try:
            with open(cache_path, 'wb') as f:
                import pickle
                pickle.dump(self.file_index_dict, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            pass

    def _start_watcher(self):
        import winreg
        def get_desktop():
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                     r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders')
                return winreg.QueryValueEx(key, "Desktop")[0]
            except:
                return os.path.expanduser("~/Desktop")

        try:
            self.observer = Observer()
            self.handler = SearchFileEventHandler(self)
            desktop_path = get_desktop()
            print(f"正在实时监控桌面: {desktop_path}")
            self.observer.schedule(self.handler, desktop_path, recursive=True)
            self.observer.start()
        except Exception as e:
            print(f"监控启动失败: {e}")

    def sync_index_hot_reload(self, path, action):
        """O(1) 极速热更新"""
        path = os.path.normpath(path)
        path_key = path.lower()
        name = os.path.basename(path)

        if name.startswith((".", "$")): return

        # O(1) 删除旧记录
        self.file_index_dict.pop(path_key, None)

        if action == "created":
            import time
            time.sleep(0.1)
            if not os.path.exists(path): return
            try:
                stat = os.stat(path)
                mtime = stat.st_mtime
                if os.path.isdir(path):
                    self.file_index_dict[path_key] = (name.lower(), name, "folder", path, "folder", -1, mtime, False)
                else:
                    _, ext = os.path.splitext(name)
                    self.file_index_dict[path_key] = (
                    name.lower(), name, ext.lower(), path, self.get_icon_type(ext), stat.st_size, mtime, False)
            except:
                pass

        self.trigger_search()

    def refresh_recycle_bin_only(self):
        try:
            # 保证主线程 COM 接口可用
            pythoncom.CoInitialize()
            shell_app = win32com.client.Dispatch("Shell.Application")
            rb = shell_app.NameSpace(10)
            if not rb: return

            # 清除旧的回收站记录
            keys_to_delete = [k for k, v in self.file_index_dict.items() if v[7]]
            for k in keys_to_delete:
                del self.file_index_dict[k]

            items = rb.Items()
            # 【修复 1】：64 (所有项目) + 128 (包括文件夹)
            items.Filter(64 + 128, "*")

            for item in items:
                try:
                    name = item.Name

                    try:
                        # item.Path 在回收站中指向真实的 $Rxxxxx.lnk 文件
                        if item.Path.lower().endswith('.lnk') and not name.lower().endswith('.lnk'):
                            name += '.lnk'
                    except Exception:
                        pass

                    orig_dir = item.ExtendedProperty("System.Recycle.DeletedFrom")
                    if not orig_dir: continue
                    # 删除了 "Windows\\Recent" in orig_dir 的判断，确保快捷方式不被误杀

                    orig_path = os.path.join(orig_dir, name)
                    path_key = orig_path.lower()

                    # 【修复 2】：文件夹获取 Size 会引发底层异常，必须独立包裹
                    try:
                        size = item.Size
                    except Exception:
                        size = -1

                    import time
                    try:
                        # 专门处理 win32com 时区 Bug 的内部小函数
                        def get_correct_ts(com_date):
                            try:
                                if not com_date: return None
                                # 核心魔法：如果有时区标签，强行剥离 (replace(tzinfo=None))，恢复纯净的本地时间
                                if hasattr(com_date, "replace"):
                                    return com_date.replace(tzinfo=None).timestamp()
                                return float(com_date)
                            except Exception:
                                return None

                        # 优先获取修改时间，拿不到再获取被删时间
                        mtime = get_correct_ts(item.ModifyDate)
                        if not mtime:
                            mtime = get_correct_ts(item.ExtendedProperty("System.Recycle.DateDeleted"))

                        # 终极兜底：当前系统真实时间
                        if not mtime:
                            mtime = time.time()
                    except Exception:
                        mtime = time.time()

                    # 写入新记录
                    self.file_index_dict[path_key] = (
                    name.lower(), name, "recycle_bin", orig_path, "recycle", size, mtime, True)
                except Exception:
                    continue
            self.trigger_search()
        except Exception as e:
            pass
        # 移除了 CoUninitialize()，避免干扰 Tkinter 主线程的剪贴板等底层组件

    def init_icons(self):
        self.icons = {}

        def create_icon(color, text=""):
            img = Image.new('RGB', (16, 16), color=color)
            draw = ImageDraw.Draw(img)
            draw.rectangle([0, 0, 15, 15], outline="gray")
            if text: draw.text((3, 0), text, fill="white")
            return ImageTk.PhotoImage(img)

        self.icons.update({
            "folder": create_icon("gold"),
            "video": create_icon("purple", "▶"),
            "image": create_icon("seagreen", "■"),
            "doc": create_icon("dodgerblue", "W"),
            "zip": create_icon("saddlebrown", "z"),
            "code": create_icon("darkslategray", "{"),
            "file": create_icon("white"),
            "recycle": create_icon("limegreen", "♻")
        })

    def get_icon_type(self, ext):
        ext = ext.lower()
        if ext in self.file_categories["视频"]: return "video"
        if ext in self.file_categories["图片"]: return "image"
        if ext in self.file_categories["文档"]: return "doc"
        if ext in self.file_categories["压缩文件"]: return "zip"
        if ext in self.file_categories["代码"]: return "code"
        return "file"

    def format_size(self, size_bytes):
        if size_bytes <= 0: return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        return f"{round(size_bytes / p, 2)} {size_name[i]}"

    def setup_ui(self):
        top_frame = tk.Frame(self.root, pady=10, padx=10)
        top_frame.pack(fill=tk.X)

        tk.Label(top_frame, text="搜索文件名:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.trigger_search())
        self.search_entry = tk.Entry(top_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=10)

        tk.Label(top_frame, text="  筛选:").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar(value="所有")
        self.filter_combo = ttk.Combobox(top_frame, textvariable=self.filter_var,
                                         values=list(self.file_categories.keys()), state="readonly", width=12)
        self.filter_combo.pack(side=tk.LEFT, padx=5)
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self.trigger_search())

        self.status_label = tk.Label(top_frame, text="准备就绪", fg="blue")
        self.status_label.pack(side=tk.RIGHT)

        mid_frame = tk.Frame(self.root, padx=10, pady=5)
        mid_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("filename", "filepath", "size", "mtime", "is_deleted")
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

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def setup_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)

    def start_fast_indexing(self):
        if self.is_indexing: return
        self.is_indexing = True
        self.file_index_dict.clear()

        drives = []
        if platform.system() == "Windows":
            drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]

        threading.Thread(target=self._fast_scan_worker, args=(drives,), daemon=True).start()

    def _fast_scan_worker(self, drives):
        pythoncom.CoInitialize()
        count = 0

        # 【修复1】：将列表倒序排序，比如变成 ['F:\', 'E:\', 'D:\', 'C:\']
        # 这样 dirs_to_scan.pop() 就会优先弹出并扫描 'C:\' 盘了！
        drives.sort(reverse=True)
        dirs_to_scan = drives[:]

        def update_status(c, d):
            self.status_label.config(text=f"扫描中 ({c} 项) ... 当前: {d[:30]}", fg="red")

        import time

        while dirs_to_scan:
            current_dir = dirs_to_scan.pop()

            # 【防止主线程卡死的 GIL 呼吸法】
            if count % 2000 == 0:
                time.sleep(0.001)

            if count % 50000 == 0:
                self.root.after(0, update_status, count, current_dir)

            try:
                with os.scandir(current_dir) as entries:
                    for entry in entries:
                        try:
                            stat = entry.stat(follow_symlinks=False)
                            path_key = entry.path.lower()
                            if entry.is_dir(follow_symlinks=False):
                                dirs_to_scan.append(entry.path)
                                self.file_index_dict[path_key] = (
                                entry.name.lower(), entry.name, "folder", entry.path, "folder", -1, stat.st_mtime,
                                False)
                            else:
                                _, ext = os.path.splitext(entry.name)
                                self.file_index_dict[path_key] = (
                                entry.name.lower(), entry.name, ext.lower(), entry.path, self.get_icon_type(ext),
                                stat.st_size, stat.st_mtime, False)
                            count += 1
                        except OSError:
                            continue
            except (PermissionError, OSError):
                continue



        # === 回收站专项扫描阶段 ===
        self.root.after(0, lambda: self.status_label.config(text="正在进行回收站深度防丢扫描...", fg="orange"))
        try:
            shell_app = win32com.client.Dispatch("Shell.Application")
            rb = shell_app.NameSpace(10)
            if rb:
                items = rb.Items()
                items.Filter(64 + 128, "*")  # 包含文件与文件夹
                for item in items:
                    try:
                        name = item.Name
                        if not name: continue

                        try:
                            # item.Path 在回收站中指向真实的 $Rxxxxx.lnk 文件
                            if item.Path.lower().endswith('.lnk') and not name.lower().endswith('.lnk'):
                                name += '.lnk'
                        except Exception:
                            pass

                        orig_dir = item.ExtendedProperty("System.Recycle.DeletedFrom")
                        if not orig_dir: continue

                        orig_path = os.path.join(orig_dir, name)
                        path_key = orig_path.lower()

                        if path_key in self.file_index_dict and self.file_index_dict[path_key][7]:
                            continue

                            # 独立保护文件夹的 Size 报错
                        try:
                            size = item.Size
                        except Exception:
                            size = -1

                        import time
                        try:
                            # 专门处理 win32com 时区 Bug 的内部小函数
                            def get_correct_ts(com_date):
                                try:
                                    if not com_date: return None
                                    # 核心魔法：如果有时区标签，强行剥离 (replace(tzinfo=None))，恢复纯净的本地时间
                                    if hasattr(com_date, "replace"):
                                        return com_date.replace(tzinfo=None).timestamp()
                                    return float(com_date)
                                except Exception:
                                    return None

                            # 优先获取修改时间，拿不到再获取被删时间
                            mtime = get_correct_ts(item.ModifyDate)
                            if not mtime:
                                mtime = get_correct_ts(item.ExtendedProperty("System.Recycle.DateDeleted"))

                            # 终极兜底：当前系统真实时间
                            if not mtime:
                                mtime = time.time()
                        except Exception:
                            mtime = time.time()

                        self.file_index_dict[path_key] = (
                        name.lower(), name, "recycle_bin", orig_path, "recycle", size, mtime, True)
                        count += 1
                    except Exception:
                        continue
        except Exception as e:
            print(f"回收站扫描异常: {e}")

        # ==========================================
        # 【核心修复】：上次漏给你的就是这最后 4 行，补上！
        # ==========================================
        self.is_indexing = False
        # 用 lambda c=count 锁死变量，确保文字准确显示数字
        self.root.after(0, lambda c=count: self.status_label.config(text=f"加载完成！共 {c} 个项目", fg="green"))
        self.root.after(0, self.perform_search)

        pythoncom.CoUninitialize()

    def _background_silent_sync(self):
        """后台静默同步：弥补离线时的文件变动，无感知更新"""
        drives = []
        if platform.system() == "Windows":
            drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        drives.sort(reverse=True)

        dirs_to_scan = drives[:]
        import time
        count = 0

        while dirs_to_scan:
            current_dir = dirs_to_scan.pop()

            if count % 500 == 0:
                time.sleep(0.01)

            try:
                with os.scandir(current_dir) as entries:
                    for entry in entries:
                        try:
                            path_key = entry.path.lower()
                            stat = entry.stat(follow_symlinks=False)
                            if path_key not in self.file_index_dict or self.file_index_dict[path_key][
                                6] != stat.st_mtime:
                                name = entry.name
                                if entry.is_dir(follow_symlinks=False):
                                    dirs_to_scan.append(entry.path)
                                    self.file_index_dict[path_key] = (
                                    name.lower(), name, "folder", entry.path, "folder", -1, stat.st_mtime, False)
                                else:
                                    _, ext = os.path.splitext(name)
                                    self.file_index_dict[path_key] = (
                                    name.lower(), name, ext.lower(), entry.path, self.get_icon_type(ext), stat.st_size,
                                    stat.st_mtime, False)

                                # 【核心修复 2】：如果在后台巡逻时发现了新文件，静默通知 UI 刷新！
                                self.trigger_search()

                            elif entry.is_dir(follow_symlinks=False):
                                dirs_to_scan.append(entry.path)
                            count += 1
                        except OSError:
                            continue
            except (PermissionError, OSError):
                continue

    def trigger_search(self):
        """核心防抖逻辑：打字时不会卡顿"""
        if self._search_timer:
            self.root.after_cancel(self._search_timer)
        self._search_timer = self.root.after(300, self.perform_search)

    def perform_search(self):
        """全量过滤生成器：精准统计匹配总数，修复多线程撞车导致的UI假死"""
        keyword = self.search_var.get().lower()
        current_filter = self.filter_var.get()
        allowed_exts = self.file_categories.get(current_filter, set())

        results = []
        match_count = 0
        is_recycle_filter = "回收站" in current_filter

        try:
            items_snapshot = list(self.file_index_dict.values())
        except RuntimeError:
            # 【核心修复 1】：遇到后台正在写数据时，千万不要直接 return 放弃！
            # 延迟 50 毫秒后再试一次，直到成功拿到快照为止，确保搜索结果一定会刷出来
            self.root.after(50, self.perform_search)
            return

        for item in items_snapshot:
            name_lower, _, ext, _, _, _, _, is_deleted = item

            if current_filter != "所有":
                if current_filter == "文件夹" and ext != "folder":
                    continue
                elif is_recycle_filter and not is_deleted:
                    continue
                elif not is_recycle_filter and current_filter != "文件夹" and ext not in allowed_exts:
                    continue

            if keyword and keyword not in name_lower: continue

            match_count += 1

            if not self.sort_col:
                if len(results) < 1000:
                    results.append(item)
            else:
                results.append(item)

        if self.sort_col:
            sort_indices = {"filename": 0, "filepath": 3, "size": 5, "mtime": 6}
            idx = sort_indices.get(self.sort_col)
            if idx is not None:
                results.sort(key=lambda x: str(x[idx]).lower() if isinstance(x[idx], str) else x[idx],
                             reverse=self.sort_reverse)

        self.current_results = results[:1000]
        self.render_treeview()

        if not keyword and current_filter == "所有":
            total_indexed = len(self.file_index_dict)
            self.status_label.config(text=f"秒开完成！共 {total_indexed} 个项目", fg="green")
        else:
            limit_tip = " (列表仅展示前1000项)" if match_count > 1000 else ""
            self.status_label.config(text=f"找到 {match_count} 个对象{limit_tip}", fg="green")

    def sort_treeview(self, col):
        if self.sort_col == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_col = col
            self.sort_reverse = False
        self._apply_sort()
        self.render_treeview()
        self._update_heading_arrows()

    def _apply_sort(self):
        sort_indices = {"filename": 0, "filepath": 3, "size": 5, "mtime": 6}
        idx = sort_indices.get(self.sort_col)
        if idx is not None:
            self.current_results.sort(key=lambda x: str(x[idx]).lower() if isinstance(x[idx], str) else x[idx],
                                      reverse=self.sort_reverse)

    def _update_heading_arrows(self):
        headings = {"filename": "名称", "filepath": "路径", "size": "大小", "mtime": "修改时间"}
        for col, text in headings.items():
            arrow = " ▼" if self.sort_reverse else " ▲" if col == self.sort_col else ""
            self.tree.heading(col, text=text + arrow)

    def render_treeview(self):
        """批量渲染技术，防止逐行插入卡顿"""
        self.tree.delete(*self.tree.get_children())  # 一次性清空，极速

        for _, orig_name, _, path, icon_key, size, mtime, is_deleted in self.current_results:
            icon = self.icons.get(icon_key, self.icons["file"])
            display_size = self.format_size(size) if size != -1 else ""
            try:
                display_time = datetime.fromtimestamp(mtime).strftime('%Y/%m/%d %H:%M')
            except:
                display_time = "未知"

            self.tree.insert("", tk.END, text="", image=icon,
                             values=(orig_name, path, display_size, display_time, is_deleted))

    def copy_path_to_clipboard(self):
        selected_items = self.tree.selection()
        if not selected_items: return
        paths = "\n".join(self.tree.item(item, "values")[1] for item in selected_items)
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(paths)
            self.root.update()
            self.status_label.config(text=f"已复制 {len(selected_items)} 条路径", fg="green")
        except Exception as e:
            messagebox.showerror("复制失败", str(e))

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
                                          command=self.restore_files)
            if len(selected_items) == 1:
                self.context_menu.add_command(label="📂 还原并打开此文件", command=self.restore_and_open_file)
            self.context_menu.add_separator()
            self.context_menu.add_command(label=f"❌ 彻底删除选中的 {len(selected_items)} 个项目",
                                          command=self.permanently_delete_files)
            self.context_menu.add_command(label="🗑️ 清空整个回收站", command=self.empty_recycle_bin)
        else:
            if len(selected_items) == 1:
                self.context_menu.add_command(label="打开 (文件/文件夹)", command=self.open_selected_file)
                self.context_menu.add_command(label="打开所在位置 (并选中)", command=self.open_folder_and_select)
                self.context_menu.add_command(label="📋 复制文件路径", command=self.copy_path_to_clipboard)
            self.context_menu.add_separator()
            self.context_menu.add_command(label=f"🗑️ 移动到回收站 ({len(selected_items)} 项)",
                                          command=self.move_to_recycle_bin)

        self.context_menu.tk_popup(event.x_root, event.y_root)

    def move_to_recycle_bin(self):
        selected_items = self.tree.selection()
        if not selected_items: return
        paths = [self.tree.item(item, "values")[1] for item in selected_items]

        if not messagebox.askyesno("移至回收站", f"确定要把这 {len(paths)} 个项目移到系统回收站吗？"): return

        success_count = 0
        try:
            for path in paths:
                if os.path.exists(path):
                    flags = shellcon.FOF_ALLOWUNDO | shellcon.FOF_NOCONFIRMATION | shellcon.FOF_SILENT | shellcon.FOF_NOERRORUI
                    res, aborted = shell.SHFileOperation((0, shellcon.FO_DELETE, path, None, flags, None, None))
                    if res == 0 and not aborted:
                        success_count += 1
                        self.file_index_dict.pop(path.lower(), None)
        except Exception as e:
            messagebox.showerror("错误", str(e))

        self.trigger_search()
        if success_count > 0:
            self.status_label.config(text=f"移至回收站: {success_count} 项", fg="green")
            # 【修复 3】：由于非桌面的文件被删不会触发 Watchdog，这里我们需要手动呼叫系统重新拉取一次回收站
            self.root.after(500, self.refresh_recycle_bin_only)

    def permanently_delete_files(self):
        selected_items = self.tree.selection()
        if not selected_items: return
        paths = [os.path.normpath(self.tree.item(item, "values")[1]).lower() for item in selected_items]

        if not messagebox.askyesno("警告", f"【危险操作】\n确定要彻底删除这 {len(paths)} 个文件吗？"): return

        try:
            pythoncom.CoInitialize()
            shell_app = win32com.client.Dispatch("Shell.Application")
            rb = shell_app.NameSpace(10)

            if rb:
                for item in rb.Items():
                    try:
                        orig_dir = item.ExtendedProperty("System.Recycle.DeletedFrom")
                        if not orig_dir: continue

                        # --- 修复补丁：对齐带 .lnk 的名称 ---
                        name = item.Name
                        try:
                            if item.Path.lower().endswith('.lnk') and not name.lower().endswith('.lnk'):
                                name += '.lnk'
                        except Exception:
                            pass
                        expected_path = os.path.join(orig_dir, name).lower()
                        # -----------------------------------

                        if expected_path in paths:
                            for verb in item.Verbs():
                                if "删除" in verb.Name or "Delete" in verb.Name:
                                    verb.DoIt()
                                    self.file_index_dict.pop(expected_path, None)
                                    break
                    except:
                        continue

            pythoncom.CoUninitialize()
            self.trigger_search()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def empty_recycle_bin(self):
        if not messagebox.askyesno("清空回收站", "【毁灭级操作】\n确定要清空系统回收站里的所有文件吗？"): return
        try:
            flags = shellcon.SHERB_NOCONFIRMATION | shellcon.SHERB_NOPROGRESSUI | shellcon.SHERB_NOSOUND
            shell.SHEmptyRecycleBin(0, None, flags)

            # 瞬间抹除索引
            keys_to_delete = [k for k, v in self.file_index_dict.items() if v[7]]
            for k in keys_to_delete: del self.file_index_dict[k]

            self.trigger_search()
            messagebox.showinfo("完成", "系统回收站已彻底清空！")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def restore_files(self):
        selected_items = self.tree.selection()
        if not selected_items: return False
        paths_to_restore = [os.path.normpath(self.tree.item(item, "values")[1]).lower() for item in selected_items]

        try:
            pythoncom.CoInitialize()
            shell_app = win32com.client.Dispatch("Shell.Application")
            rb = shell_app.NameSpace(10)

            if rb:
                for item in rb.Items():
                    try:
                        orig_dir = item.ExtendedProperty("System.Recycle.DeletedFrom")
                        if not orig_dir: continue

                        # --- 修复补丁：对齐带 .lnk 的名称 ---
                        name = item.Name
                        try:
                            if item.Path.lower().endswith('.lnk') and not name.lower().endswith('.lnk'):
                                name += '.lnk'
                        except Exception:
                            pass
                        expected_path = os.path.join(orig_dir, name).lower()
                        # -----------------------------------

                        if expected_path in paths_to_restore:
                            for verb in item.Verbs():
                                if "还原" in verb.Name or "Restore" in verb.Name or "undelete" in verb.Name.lower():
                                    verb.DoIt()
                                    # 删除回收站记录
                                    self.file_index_dict.pop(expected_path, None)
                                    # 重新触发文件扫描
                                    self.sync_index_hot_reload(expected_path, "created")
                                    break
                    except:
                        continue

            pythoncom.CoUninitialize()
            return True
        except Exception as e:
            return False

    def get_selected_filepath(self):
        selected = self.tree.selection()
        return self.tree.item(selected[0], "values")[1] if selected else None

    def restore_and_open_file(self):
        file_path = self.get_selected_filepath()
        if self.restore_files() and os.path.exists(file_path):
            try:
                os.startfile(file_path)
            except:
                pass

    def on_double_click(self, event):
        selected = self.tree.selection()
        if not selected: return
        is_deleted = (str(self.tree.item(selected[0], "values")[4]) == 'True')

        if is_deleted:
            self.restore_and_open_file()
        else:
            self.open_selected_file()

    def open_selected_file(self):
        file_path = self.get_selected_filepath()
        if file_path and os.path.exists(file_path):
            try:
                os.startfile(file_path)
            except:
                pass

    def open_folder_and_select(self):
        file_path = self.get_selected_filepath()
        if file_path and os.path.exists(file_path):
            try:
                subprocess.run(['explorer', '/select,', os.path.normpath(file_path)])
            except:
                pass

    def quit_from_tray(self, icon, item):
        icon.stop()
        self.save_cache()  # <--- 退出前保存内存快照
        self.root.after(0, self.root.destroy)

    def on_closing(self):
        response = messagebox.askyesnocancel("退出提示", "点击【是】直接退出\n点击【否】最小化到系统托盘\n点击【取消】返回")
        if response is True:
            self.status_label.config(text="正在保存索引快照，请稍候...", fg="red")
            self.root.update()
            self.save_cache()  # <--- 直接退出前保存
            self.root.destroy()
        elif response is False:
            self.hide_to_tray()

    def create_tray_image(self):
        try:
            return Image.open(get_resource_path("app_icon.ico"))
        except:
            img = Image.new('RGB', (64, 64), color=(0, 120, 215))
            ImageDraw.Draw(img).ellipse((16, 16, 40, 40), outline="white", width=4)
            return img

    def hide_to_tray(self):
        self.root.withdraw()
        if 'pystray' in sys.modules:
            menu = pystray.Menu(pystray.MenuItem('显示面板', self.show_from_tray, default=True),
                                pystray.MenuItem('完全退出', self.quit_from_tray))
            self.tray_icon = pystray.Icon("SuperSearch", self.create_tray_image(), "Super Search", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        else:
            self.root.destroy()

    def show_from_tray(self, icon, item):
        icon.stop()
        self.root.after(0, self.root.deiconify)

    def quit_from_tray(self, icon, item):
        icon.stop()
        self.root.after(0, self.root.destroy)


if __name__ == "__main__":
    root = tk.Tk()
    app = MiniEverything(root)
    root.mainloop()