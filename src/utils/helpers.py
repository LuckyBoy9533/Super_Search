# src/utils/helpers.py
import os
import sys
import math


def get_resource_path(relative_path: str) -> str:
    """
    获取静态资源（如图标）的绝对路径。
    核心魔法：能完美兼容 PyInstaller 打包后的临时解压目录（_MEIPASS）。
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)

    # 精准定位：当前文件在 src/utils/helpers.py
    # 向上退三级回到项目根目录 (Super_Search/)
    current_dir = os.path.abspath(os.path.dirname(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir))

    return os.path.join(root_dir, relative_path)


def get_data_path(filename: str) -> str:
    """
    专门用于读写持久化数据（如 .pkl 索引缓存文件）。
    确保缓存文件永远和最终的 exe 文件（或项目根目录）挨在一起，而不是写进 C 盘深处。
    """
    if getattr(sys, 'frozen', False):
        # 如果是打包后的 exe 运行环境
        base_dir = os.path.dirname(sys.executable)
    else:
        # 如果是 py 脚本运行环境，将缓存放在项目的 src/ 同级目录下
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(os.path.dirname(current_dir))

    return os.path.join(base_dir, filename)


def format_size(size_bytes: int) -> str:
    """
    将枯燥的字节数转换为人类可读的文件大小 (KB, MB, GB...)
    """
    if size_bytes <= 0:
        return "0 B"

    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)

    return f"{round(size_bytes / p, 2)} {size_name[i]}"