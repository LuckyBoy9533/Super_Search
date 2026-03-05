# src/utils/icons.py
from PIL import Image, ImageDraw, ImageTk
from typing import Dict, Any

from config import FILE_CATEGORIES

def get_icon_type(ext: str) -> str:
    """
    根据文件后缀名，返回对应的图标类型标记（字符串）。
    这个函数是纯逻辑判定，可以安全地在后台扫盘的子线程中调用。
    """
    ext = ext.lower()
    if ext in FILE_CATEGORIES.get("视频", set()): return "video"
    if ext in FILE_CATEGORIES.get("图片", set()): return "image"
    if ext in FILE_CATEGORIES.get("文档", set()): return "doc"
    if ext in FILE_CATEGORIES.get("压缩文件", set()): return "zip"
    if ext in FILE_CATEGORIES.get("代码", set()): return "code"
    return "file"

class IconManager:
    """
    Tkinter 界面图标管理器。
    负责在内存中通过 PIL 动态绘制并缓存各种小图标。
    必须在主界面的主线程中被实例化。
    """
    def __init__(self):
        self.icons: Dict[str, ImageTk.PhotoImage] = {}
        self._init_icons()

    def _create_icon(self, color: str, text: str = "") -> ImageTk.PhotoImage:
        """内部绘图引擎：在 16x16 的画布上画出色块和文字"""
        img = Image.new('RGB', (16, 16), color=color)
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, 15, 15], outline="gray")
        if text:
            draw.text((3, 0), text, fill="white")
        return ImageTk.PhotoImage(img)

    def _init_icons(self) -> None:
        """预生成所有类别的图标，存入字典实现 O(1) 极速读取"""
        self.icons.update({
            "folder": self._create_icon("gold"),
            "video": self._create_icon("purple", "▶"),
            "image": self._create_icon("seagreen", "■"),
            "doc": self._create_icon("dodgerblue", "W"),
            "zip": self._create_icon("saddlebrown", "z"),
            "code": self._create_icon("darkslategray", "{"),
            "file": self._create_icon("white"),
            "recycle": self._create_icon("limegreen", "♻")
        })

    def get_icon(self, icon_key: str) -> ImageTk.PhotoImage:
        """
        供前端 UI 层调用，获取对应的图片对象。
        如果找不到对应的 key，安全地兜底返回白色默认文件图标。
        """
        return self.icons.get(icon_key, self.icons["file"])