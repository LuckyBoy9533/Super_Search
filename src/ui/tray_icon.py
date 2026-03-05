# src/ui/tray_icon.py
import sys
import threading
from typing import Callable, Any

try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None

# 引入配置与工具（下一步会实现）
from config import APP_NAME
from utils.helpers import get_resource_path
from config import ICON_FILENAME


class TrayManager:
    """系统托盘后台挂机管理器"""

    def __init__(self, root: Any, on_quit_callback: Callable):
        self.root = root
        self.on_quit_callback = on_quit_callback
        self.tray_icon = None

    def create_tray_image(self) -> "Image.Image":
        try:
            return Image.open(get_resource_path(ICON_FILENAME))
        except Exception:
            # 如果找不到图标，画一个临时的蓝色圆圈兜底
            img = Image.new('RGB', (64, 64), color=(0, 120, 215))
            ImageDraw.Draw(img).ellipse((16, 16, 40, 40), outline="white", width=4)
            return img

    def show_from_tray(self, icon: pystray.Icon, item: pystray.MenuItem):
        """从托盘唤醒主界面"""
        icon.stop()
        self.root.after(0, self.root.deiconify)

    def quit_from_tray(self, icon: pystray.Icon, item: pystray.MenuItem):
        """完全退出程序"""
        icon.stop()
        self.root.after(0, self.on_quit_callback)

    def hide_to_tray(self):
        """隐藏主界面，挂载到系统托盘"""
        self.root.withdraw()

        if pystray is None:
            # 如果用户没装 pystray，直接退出
            self.on_quit_callback()
            return

        menu = pystray.Menu(
            item('显示面板', self.show_from_tray, default=True),
            item('完全退出', self.quit_from_tray)
        )

        self.tray_icon = pystray.Icon("SuperSearch", self.create_tray_image(), APP_NAME, menu)
        # 必须在独立线程运行，否则会卡死 Tkinter
        threading.Thread(target=self.tray_icon.run, daemon=True).start()