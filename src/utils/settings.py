
# src/utils/settings.py
import json
import os
import logging

from config import APP_NAME

logger = logging.getLogger(__name__)

# 定义配置文件路径
# C:\Users\YourUser\.config\SuperSearch\settings.json
SETTINGS_DIR = os.path.join(os.path.expanduser("~/.config"), APP_NAME)
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")

# 默认设置
DEFAULT_SETTINGS = {
    "language": "zh"
}

def get_settings_path() -> str:
    """获取配置文件绝对路径"""
    return SETTINGS_FILE

def load_settings() -> dict:
    """加载配置文件，如果文件不存在则创建并写入默认配置"""
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    if not os.path.exists(SETTINGS_FILE):
        logger.warning(f"Settings file not found. Creating default settings at {SETTINGS_FILE}")
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS

    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            # 确保所有默认键都存在
            for key, value in DEFAULT_SETTINGS.items():
                if key not in settings:
                    settings[key] = value
            logger.info(f"Settings loaded from {SETTINGS_FILE}")
            return settings
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load settings file: {e}. Using default settings.")
        # 如果文件损坏或无法读取，使用默认设置并尝试覆盖损坏的文件
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS

def save_settings(settings: dict) -> None:
    """将配置字典写入到 setting.json 文件"""
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
            logger.info(f"Settings saved to {SETTINGS_FILE}")
    except IOError as e:
        logger.error(f"Failed to save settings to {SETTINGS_FILE}: {e}")
