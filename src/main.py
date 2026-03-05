# src/main.py
import ctypes
import logging
import sys
import os
import tkinter as tk

# 引入配置模块
from config import APP_ID, setup_logging

from core.engine import SearchEngine
from core.watcher import FileWatcher
from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def is_admin() -> bool:
    """检查当前是否具有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin():
    """触发 Windows UAC 弹窗，以管理员身份重新运行本程序"""
    logger.warning("当前无管理员权限，正在申请提权...")

    # 获取当前运行的 Python 解释器路径和脚本路径
    script = os.path.abspath(sys.argv[0])
    # 处理可能存在的启动参数
    params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])

    try:
        # 核心魔法："runas" 会告诉 Windows 弹出 UAC 权限请求框
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
    except Exception as e:
        logger.error(f"提权失败: {e}")

    # 唤起管理员版本后，立刻退出当前的普通权限版本
    sys.exit(0)


def set_windows_app_id() -> None:
    """设置 AppUserModelID 解决任务栏图标问题"""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        logger.info(f"Windows App ID set to: {APP_ID}")
    except Exception as e:
        logger.warning(f"Failed to set Windows App ID: {e}")


def main() -> None:
    """程序主入口函数"""
    setup_logging()

    # ==========================================
    # 【新增】权限拦截器：如果不是管理员，立刻提权重载
    # ==========================================
    if not is_admin():
        run_as_admin()
        return  # 确保普通权限的进程不再往下走

    logger.info("Starting Super Search initialization with Admin privileges...")
    set_windows_app_id()

    root = tk.Tk()

    logger.info("Initializing core search engine...")
    engine = SearchEngine()

    app_window = MainWindow(root, engine)

    logger.info("Starting background file watcher...")
    watcher = FileWatcher(engine)
    watcher.start()

    engine.on_data_updated = app_window.refresh_ui

    logger.info("Initialization complete. Entering UI main loop.")
    root.mainloop()


if __name__ == "__main__":
    main()