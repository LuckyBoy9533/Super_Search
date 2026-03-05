# src/core/watcher.py
import os
import winreg
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Any

logger = logging.getLogger(__name__)


class SearchFileEventHandler(FileSystemEventHandler):
    """事件处理器：将操作系统的文件变动通知给搜索引擎"""

    def __init__(self, engine: Any):
        self.engine = engine

    def on_any_event(self, event):
        try:
            if event.event_type == 'created':
                self.engine.sync_index_hot_reload(event.src_path, "created")
            elif event.event_type == 'deleted':
                self.engine.sync_index_hot_reload(event.src_path, "deleted")
            elif event.event_type == 'moved':
                self.engine.sync_index_hot_reload(event.src_path, "deleted")
                self.engine.sync_index_hot_reload(event.dest_path, "created")

            # 触发回收站扫描防抖
            self.engine.trigger_recycle_bin_refresh()
        except Exception as e:
            logger.error(f"Watchdog 事件处理异常: {e}")


class FileWatcher:
    """Watchdog 监控管理器"""

    def __init__(self, engine: Any):
        self.engine = engine
        self.observer = Observer()
        self.handler = SearchFileEventHandler(self.engine)
        self.desktop_path = self._get_desktop_path()

    def _get_desktop_path(self) -> str:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders')
            return winreg.QueryValueEx(key, "Desktop")[0]
        except Exception:
            return os.path.expanduser("~/Desktop")

    def start(self):
        try:
            logger.info(f"正在实时监控目录: {self.desktop_path}")
            self.observer.schedule(self.handler, self.desktop_path, recursive=True)
            self.observer.start()
        except Exception as e:
            logger.error(f"监控启动失败: {e}")

    def stop(self):
        self.observer.stop()
        self.observer.join()