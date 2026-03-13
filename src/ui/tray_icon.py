# src/ui/tray_icon.py
import threading
from typing import Callable, Any

import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as item

# 导入配置与国际化
from config import APP_NAME, ICON_FILENAME
from utils.helpers import get_resource_path
from .locales import get_text


class TrayManager:
    """系统托盘后台挂机管理器"""

    def __init__(self, main_window: Any, root: Any):
        self.main_window = main_window
        self.root = root
        self.tray_icon = None

    def create_tray_image(self) -> Image.Image:
        try:
            return Image.open(get_resource_path(ICON_FILENAME))
        except Exception:
            img = Image.new('RGB', (64, 64), color=(0, 120, 215))
            ImageDraw.Draw(img).ellipse((16, 16, 40, 40), outline="white", width=4)
            return img

    def show_from_tray(self, icon: pystray.Icon, menu_item: pystray.MenuItem):
        self.stop()
        self.root.after(0, self.root.deiconify)

    def quit_from_tray(self, icon: pystray.Icon, menu_item: pystray.MenuItem):
        self.stop()
        self.root.after(0, self.main_window.full_quit)

    def hide_to_tray(self):
        self.root.withdraw()

        menu = pystray.Menu(
            item(get_text("tray_show"), self.show_from_tray, default=True),
            item(get_text("tray_quit"), self.quit_from_tray)
        )

        self.tray_icon = pystray.Icon(APP_NAME, self.create_tray_image(), APP_NAME, menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def stop(self):
        if self.tray_icon:
            self.tray_icon.stop()