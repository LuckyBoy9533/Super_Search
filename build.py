# build.py
import os
import sys
import subprocess
import shutil


def create_version_info():
    """动态生成 Windows Version Info 配置文件"""
    print("📝 正在生成 Windows 文件属性与元数据...")
    version_info_str = """
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 1, 0, 0),
    prodvers=(1, 1, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'080404b0',
        [StringStruct(u'Developer', u'Barry Allen'),
         StringStruct(u'FileDescription', u'Super Search (极速本地搜索)'),
         StringStruct(u'FileVersion', u'1.1.0'),
         StringStruct(u'InternalName', u'SuperSearch'),
         StringStruct(u'LegalCopyright', u'Copyright (c) 2026 Barry Allen. All rights reserved.'),
         StringStruct(u'OriginalFilename', u'SuperSearch.exe'),
         StringStruct(u'ProductName', u'Super Search'),
         StringStruct(u'ProductVersion', u'1.1.0')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [2052, 1200])])
  ]
)
"""
    with open("version_info.txt", "w", encoding="utf-8") as f:
        f.write(version_info_str)


def clean_build_dirs():
    """清理历史构建缓存"""
    print("🧹 正在清理旧的构建文件夹...")
    for dir_name in ['build', 'dist', '__pycache__']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    for file_name in ['SuperSearch.spec', 'version_info.txt']:
        if os.path.exists(file_name):
            os.remove(file_name)


def build_exe():
    """调用 PyInstaller 进行企业级打包"""
    print("🚀 开始构建带有企业级元数据的 Super Search...")

    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)

    # PyInstaller 构建参数
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=SuperSearch",
        "--icon=assets/app_icon.ico",
        "--version-file=version_info.txt",
        "--add-data=assets;assets",

        "--paths=src",  # <--- 【就是新增这一行！】告诉 PyInstaller 源码搜索路径

        # 👇【修复核心】强制将 win32com 的隐藏时间依赖库打包进去 👇
        "--hidden-import=win32timezone",

        "src/main.py"
    ]

    try:
        subprocess.run(pyinstaller_args, check=True)
        print("\n✅ 构建大功告成！")
        print("📁 发行版已生成在: dist/SuperSearch/ 目录下")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 构建失败，错误代码: {e}")


if __name__ == "__main__":
    try:
        import PyInstaller
    except ImportError:
        print("⚠️ 尚未安装 PyInstaller，正在自动安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    clean_build_dirs()
    create_version_info()
    build_exe()