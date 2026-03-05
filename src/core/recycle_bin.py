# src/core/recycle_bin.py
import os
import time
import logging
import pythoncom
import win32com.client
from win32com.shell import shell, shellcon
from typing import List, Tuple, Any

logger = logging.getLogger(__name__)


class RecycleBinManager:
    """Windows 系统回收站操作封装 (相当于底层驱动层)"""

    @staticmethod
    def _get_correct_ts(com_date: Any) -> float:
        """专门处理 win32com 时区 Bug 的内部工具函数"""
        try:
            if not com_date:
                return time.time()
            if hasattr(com_date, "replace"):
                return com_date.replace(tzinfo=None).timestamp()
            return float(com_date)
        except Exception:
            return time.time()

    @classmethod
    def get_all_items(cls) -> List[Tuple]:
        """扫描并返回回收站中的所有项目记录"""
        items_data = []
        try:
            pythoncom.CoInitialize()
            shell_app = win32com.client.Dispatch("Shell.Application")
            rb = shell_app.NameSpace(10)
            if not rb: return []

            items = rb.Items()
            items.Filter(64 + 128, "*")

            for item in items:
                try:
                    name = item.Name
                    if item.Path.lower().endswith('.lnk') and not name.lower().endswith('.lnk'):
                        name += '.lnk'

                    orig_dir = item.ExtendedProperty("System.Recycle.DeletedFrom")
                    if not orig_dir: continue
                    orig_path = os.path.join(orig_dir, name)

                    try:
                        size = item.Size
                    except Exception:
                        size = -1

                    mtime = cls._get_correct_ts(item.ModifyDate)
                    if not mtime: mtime = cls._get_correct_ts(item.ExtendedProperty("System.Recycle.DateDeleted"))

                    # 【核心修改】：元组扩容到 9 个元素，最后一个是底层真实物理路径 item.Path
                    items_data.append(
                        (name.lower(), name, "recycle_bin", orig_path, "recycle", size, mtime, True, item.Path))
                except Exception as e:
                    continue
        except Exception as e:
            logger.error(f"回收站扫描异常: {e}")
        finally:
            pythoncom.CoUninitialize()

        return items_data

    @classmethod
    def empty_bin(cls) -> bool:
        """清空系统回收站"""
        try:
            flags = shellcon.SHERB_NOCONFIRMATION | shellcon.SHERB_NOPROGRESSUI | shellcon.SHERB_NOSOUND
            shell.SHEmptyRecycleBin(0, None, flags)
            return True
        except Exception as e:
            logger.error(f"清空回收站失败: {e}")
            raise e

    @classmethod
    def permanently_delete(cls, target_paths: List[str]) -> bool:
        """彻底粉碎指定文件（现接收底层真实路径）"""
        target_paths = [os.path.normpath(p).lower() for p in target_paths]
        try:
            pythoncom.CoInitialize()
            shell_app = win32com.client.Dispatch("Shell.Application")
            rb = shell_app.NameSpace(10)
            if rb:
                for item in rb.Items():
                    try:
                        # 【核心优化】：极其精准的匹配，告别复杂的字符判断
                        if item.Path.lower() in target_paths:
                            for verb in item.Verbs():
                                if "删除" in verb.Name or "Delete" in verb.Name:
                                    verb.DoIt()
                                    break
                    except Exception:
                        continue
            return True
        finally:
            pythoncom.CoUninitialize()

    @classmethod
    def restore_files(cls, target_paths: List[str]) -> bool:
        """还原指定文件（现接收底层真实路径）"""
        target_paths = [os.path.normpath(p).lower() for p in target_paths]
        try:
            pythoncom.CoInitialize()
            shell_app = win32com.client.Dispatch("Shell.Application")
            rb = shell_app.NameSpace(10)
            if rb:
                for item in rb.Items():
                    try:
                        # 【核心优化】：极其精准的匹配
                        if item.Path.lower() in target_paths:
                            for verb in item.Verbs():
                                if "还原" in verb.Name or "Restore" in verb.Name or "undelete" in verb.Name.lower():
                                    verb.DoIt()
                                    break
                    except Exception:
                        continue
            return True
        finally:
            pythoncom.CoUninitialize()