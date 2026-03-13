# src/core/engine.py
import os
import time
import string
import platform
import threading
import logging
import pickle
from typing import Callable, Optional, List, Tuple

from config import CACHE_FILENAME, FILE_CATEGORIES
from .recycle_bin import RecycleBinManager

# 下一步要创建的工具库
from utils import get_data_path, get_icon_type

logger = logging.getLogger(__name__)


class SearchEngine:
    """搜索与索引核心引擎"""

    def __init__(self):
        self.file_index_dict = {}
        self.is_indexing = False

        # UI 回调钩子 (依赖注入，供外部绑定)
        self.on_scan_progress: Optional[Callable[[int, str], None]] = None
        self.on_scan_complete: Optional[Callable[[int], None]] = None
        self.on_data_updated: Optional[Callable[[], None]] = None
        self.on_status_msg: Optional[Callable[[str, str], None]] = None

        self._rb_timer = None

    def load_cache(self) -> bool:
        cache_path = get_data_path(CACHE_FILENAME)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)
                    # 【核心防护】：如果发现是旧版本的缓存数据(长度不为9)，直接放弃加载并重新扫盘
                    if data and len(next(iter(data.values()))) != 9:
                        logger.warning("发现旧版缓存数据格式不兼容，正在重新进行全盘扫描...")
                        return False
                    self.file_index_dict = data
                return True
            except Exception as e:
                logger.error(f"加载缓存失败: {e}")
                return False
        return False

    def save_cache(self) -> None:
        cache_path = get_data_path(CACHE_FILENAME)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(self.file_index_dict, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info("索引快照保存成功")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")

    def sync_index_hot_reload(self, path: str, action: str):
        path = os.path.normpath(path)
        path_key = path.lower()
        name = os.path.basename(path)

        if name.startswith((".", "$")): return
        self.file_index_dict.pop(path_key, None)

        if action == "created":
            time.sleep(0.1)
            if not os.path.exists(path): return
            try:
                stat = os.stat(path)
                mtime = stat.st_mtime
                if os.path.isdir(path):
                    # 补上第9个参数：path
                    self.file_index_dict[path_key] = (
                    name.lower(), name, "folder", path, "folder", -1, mtime, False, path)
                else:
                    _, ext = os.path.splitext(name)
                    # 补上第9个参数：path
                    self.file_index_dict[path_key] = (
                    name.lower(), name, ext.lower(), path, get_icon_type(ext), stat.st_size, mtime, False, path)
            except Exception:
                pass

        if self.on_data_updated:
            self.on_data_updated()

    def start_fast_indexing(self):
        if self.is_indexing: return
        self.is_indexing = True
        self.file_index_dict.clear()

        drives = []
        if platform.system() == "Windows":
            drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]

        threading.Thread(target=self._fast_scan_worker, args=(drives,), daemon=True).start()

    def _fast_scan_worker(self, drives: List[str]):
        count = 0
        drives.sort(reverse=True)
        dirs_to_scan = drives[:]

        while dirs_to_scan:
            current_dir = dirs_to_scan.pop()
            if count % 2000 == 0: time.sleep(0.001)
            if count % 50000 == 0 and self.on_scan_progress:
                self.on_scan_progress(count, current_dir)

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
                                False, entry.path)
                            else:
                                _, ext = os.path.splitext(entry.name)
                                self.file_index_dict[path_key] = (
                                entry.name.lower(), entry.name, ext.lower(), entry.path, get_icon_type(ext),
                                stat.st_size, stat.st_mtime, False, entry.path)
                            count += 1
                        except OSError:
                            continue
            except (PermissionError, OSError):
                continue

        if self.on_status_msg:
            self.on_status_msg("正在进行回收站深度防丢扫描...", "orange")
        self.refresh_recycle_bin()
        count = len(self.file_index_dict)

        self.is_indexing = False
        if self.on_scan_complete:
            self.on_scan_complete(count)

    def refresh_recycle_bin(self):
        keys_to_delete = [k for k, v in self.file_index_dict.items() if v[7]]
        for k in keys_to_delete:
            del self.file_index_dict[k]

        rb_items = RecycleBinManager.get_all_items()
        for item in rb_items:
            # 【核心修改】：使用回收站的物理乱码路径(item[8])作为极速防撞Key
            path_key = item[8].lower()
            self.file_index_dict[path_key] = item

    def trigger_recycle_bin_refresh(self):
        """提供给 watcher 的防抖刷新入口（使用底层独立 Timer，彻底解耦 UI）"""
        if self._rb_timer is not None:
            self._rb_timer.cancel()

        def _task():
            try:
                self.refresh_recycle_bin()
                if self.on_data_updated:
                    self.on_data_updated()
            except Exception as e:
                logger.error(f"后台刷新回收站失败: {e}")

        # 延迟 1 秒后在独立后台线程执行刷新，避免高频 IO 卡死
        import threading
        self._rb_timer = threading.Timer(1.0, _task)
        self._rb_timer.start()

    def perform_search(self, keyword: str, current_filter: str, sort_col: str = None, sort_reverse: bool = False) -> \
    Tuple[List[Tuple], int]:
        keyword = keyword.lower()
        allowed_exts = FILE_CATEGORIES.get(current_filter, set())

        results = []
        match_count = 0

        try:
            items_snapshot = list(self.file_index_dict.values())
        except RuntimeError:
            return [], -1

        for item in items_snapshot:
            name_lower, _, ext, _, _, _, _, is_deleted, _ = item

            # 【核心修复】根据中立的 category_key 进行过滤
            if current_filter != "category_all":
                if current_filter == "category_folder":
                    if ext != "folder": continue
                elif current_filter == "category_recycle_bin":
                    if not is_deleted: continue
                elif ext not in allowed_exts:
                    continue

            if keyword and keyword not in name_lower: continue
            match_count += 1

            if not sort_col:
                if len(results) < 1000: results.append(item)
            else:
                results.append(item)

        if sort_col:
            sort_indices = {"filename": 0, "filepath": 3, "size": 5, "mtime": 6}
            idx = sort_indices.get(sort_col)
            if idx is not None:
                results.sort(key=lambda x: str(x[idx]).lower() if isinstance(x[idx], str) else x[idx],
                             reverse=sort_reverse)

        return results[:1000], match_count