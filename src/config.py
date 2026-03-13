# src/config.py
import logging
import sys
import os

# --- 应用基础信息 ---
APP_NAME = "Super Search"
APP_VERSION = "1.2.0"
# 用于 Windows 任务栏图标隔离的 App ID
APP_ID = f"luckyboy.supersearch.v{APP_VERSION}"

# --- 存储与资源配置 ---
CACHE_FILENAME = "index_cache.pkl"
ICON_FILENAME = "assets/app_icon.ico"  # 【修复】恢复正确的图标文件名
# 快速启动时，列表最大显示的项目数 (避免UI卡顿)
UI_DISPLAY_LIMIT = 1000

# ==========================================
# 国际化与本地化 (i18n)
# ==========================================
# 语言配置文件 (此项不应被用户直接修改)
# settings.json 中的 'language' 会覆盖此默认值
DEFAULT_LANGUAGE = "zh"

# --- 智能分类字典 ---
# 【改造】使用与语言无关的中立 key
FILE_CATEGORIES: dict[str, set[str]] = {
    "category_all": set(),
    "category_audio": {".mp3", ".wav", ".flac"},
    "category_video": {".mp4", ".mkv", ".avi", ".mov"},
    "category_image": {".png", ".jpg", ".jpeg", ".gif", ".ico"},
    "category_document": {".doc", ".docx", ".pdf", ".txt", ".md", ".xlsx"},
    "category_archive": {".zip", ".rar", ".7z"},
    "category_code": {".py", ".java", ".c", ".cpp", ".html", ".css", ".js"},
    "category_folder": {"folder"},
    "category_recycle_bin": {"recycle_bin"}
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