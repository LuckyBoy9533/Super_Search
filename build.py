import os
import shutil
import sys
import PyInstaller.__main__


def clean_build_dirs():
    """清理旧的构建产物，保持环境干净"""
    print("🧹 正在清理历史构建产物...")
    for item in ['build', 'dist', 'SuperSearch.spec']:
        if os.path.exists(item):
            if os.path.isdir(item):
                shutil.rmtree(item)
            else:
                os.remove(item)
            print(f"   已删除: {item}")


def build_app():
    """执行 PyInstaller 核心打包逻辑"""
    print("🚀 开始全自动打包 SuperSearch...")

    # 自动识别操作系统的路径分隔符 (Windows 是 ';', Linux/Mac 是 ':')
    # 虽然咱们主要针对 Windows，但写严谨一点更显专业
    add_data_separator = os.pathsep

    # 组装 PyInstaller 参数列表
    # 这些都是我们踩过坑后总结出的“完美配方”
    params = [
        'src/main.py',  # 1. 启动入口
        '--name=SuperSearch',  # 2. 生成的 exe 名称
        '--onefile',  # 3. 单文件模式 (最干净的发布方式)
        '--windowed',  # 4. 隐藏背后的黑色控制台
        '--icon=assets/app_icon.ico',  # 5. 指定软件图标
        '--paths=src',  # 6. 解决自建包(如 src.config)找不到的问题
        '--hidden-import=config',  # 7. 强制挂载配置文件
        '--hidden-import=win32com.client',  # 8. 强行绑架 Windows COM 接口 (查回收站必备)
        '--hidden-import=pythoncom',  # 9. 强行绑架底层的 COM C++ 库
        '--hidden-import=win32timezone',  # 10. 修复由于文件时间转换导致的潜在崩溃
        f'--add-data=assets{add_data_separator}assets',  # 11. 将本地的图标图片资源打包进去
        '--clean',  # 12. 每次打包前清理缓存，防止幽灵 Bug
        '-y'  # 13. 自动确认覆盖
    ]

    # 调用 PyInstaller 引擎
    PyInstaller.__main__.run(params)


if __name__ == "__main__":
    # 确保当前安装了 pyinstaller
    try:
        import PyInstaller
    except ImportError:
        print("❌ 错误: 未安装 PyInstaller 工具。")
        print("💡 请先在终端运行: pip install pyinstaller")
        sys.exit(1)

    clean_build_dirs()
    build_app()

    print("\n" + "=" * 50)
    print("🎉 打包大功告成！")
    print("👉 请在项目目录的 'dist' 文件夹中获取 SuperSearch.exe")
    print("=" * 50)