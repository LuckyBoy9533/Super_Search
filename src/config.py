# src/config.py
import logging
import sys
import os

# --- 应用基础信息 ---
APP_NAME = "Super Search"
APP_VERSION = "1.1.0"
# 用于 Windows 任务栏图标隔离的 App ID
APP_ID = 'my_personal.super_search.version.1.1'

# --- 存储与资源配置 ---
CACHE_FILENAME = "index_cache.pkl"
ICON_FILENAME = os.path.join("assets", "app_icon.ico")

# --- 智能分类字典 ---
# 将原先在 MiniEverything 内部的字典抽离出来成为全局常量
FILE_CATEGORIES: dict[str, set[str]] = {
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

# --- 企业级日志配置 ---
def setup_logging() -> None:
    """初始化全局日志系统"""
    # 如果是打包后的 exe，可以考虑将日志输出到文件；开发环境下输出到控制台
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
            # 企业级应用通常会加上 FileHandler：
            # logging.FileHandler("super_search.log", encoding="utf-8")
        ]
    )