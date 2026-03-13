# English | 简体中文

# Super Search (极速本地搜索工具)
   
这是一个基于 Python 开发的 Windows 极速本地文件检索工具，旨在提供类似 "Everything" 的毫秒级搜索体验。不仅具备极快的文件检索能力，还深度融合了 Windows 系统的底层 API，支持系统回收站的深度管理、文件系统的实时无感监控，以及完备的多语言支持。

## ⬇️ 快速下载与使用指南

对于普通用户，无需配置复杂的开发环境，直接下载打包好的可执行程序即可：

🚀 **小白用户请点此一键跳转下载最新版 Windows 免安装程序 (.zip)**

1. 点击上方链接，前往 GitHub 的 Releases 发布页。
2. 找到最新版本，下载名为 `Super_Search_vX.X.X_Windows.zip` 的压缩包。
3. 将压缩包解压到你电脑上的任意位置。
4. 双击运行文件夹内的 `SuperSearch.exe` 即可体验极速搜索！(完全免安装，绿色纯净不写注册表)。

## ✨ 核心特性

* **⚡ 极速加载与检索：** 基于内存字典（Dict）实现了 O(1) 复杂度的极速去重和检索，配合本地快照缓存（.pkl），实现应用秒开。
* **♻️ 回收站深度联动：** 打破常规搜索软件的盲区，深度集成 Windows COM 接口，支持直接在搜索结果中查看、还原、彻底删除回收站文件，无惧同名文件覆盖，甚至一键清空回收站。
* **👀 实时目录监控：** 底层接入 watchdog 引擎，实时监听本地（如桌面）的文件创建、删除、移动，实现索引数据的热更新与静默防抖刷新。
* **🌍 国际化多语言支持：** 内置完整的 i18n 架构，支持一键在“简体中文”与“English”之间无缝实时切换，主界面、右键菜单及底层状态提示全覆盖。
* **🗂️ 智能分类筛选：** 内置丰富的格式字典，一键分类检索图片、视频、音频、文档、压缩包与代码文件。
* **💻 纯净后台体验：** 集成 pystray，支持一键最小化至系统托盘静默挂机，随时唤醒，不打扰日常工作。

## 📸 界面预览与使用说明

本工具采用开箱即用的设计理念，无需复杂配置即可获得极速的搜索体验。

> **💡 强烈建议：程序启动时会自动请求【管理员身份】运行** > 由于 Windows 系统的权限隔离机制，以管理员身份运行可以最大限度地遍历底层目录结构。根据实测对比，管理员模式下可多扫描出近 80,000 个深度或系统级文件，确保您的搜索绝对“无死角”。

*(对比演示：普通权限扫描结果 vs 管理员权限扫描结果)*

### 🌟 核心功能演示

* **异步扫盘与搜索:** 程序支持在后台全盘扫描的同时进行关键词检索。但为了确保搜索结果 100% 完整，建议首次运行时，等待底部状态栏提示“加载完成”后再进行高频使用。
* **精准筛选与右键操作:** 顶部支持按“文档、图片、视频、代码”等大类进行极速过滤。在搜索结果中，您可以直接通过右键菜单对文件执行：打开、打开所在位置、复制路径或彻底删除等操作。*(小贴士：按住 Ctrl 或 Shift 键点击列表，可实现文件的批量多选与操作)*
* **实时语言切换:** 顶部导航栏提供语言下拉框，无论是中文用户还是英文开发者，都能获得最原生的使用体验。
* **♻️ 独家特性：回收站深度联动:** 列表中带有绿色 ♻ 图标的项目代表当前处于“系统回收站”中的文件。您可以直接在搜索结果中右键点击它们，执行精准还原或彻底粉碎，无需再繁琐地去翻找系统回收站。

### 💻 后台挂机与秒开机制

* **系统托盘静默守护:** 当您点击主界面的关闭按钮时，程序默认会最小化至右下角的系统托盘，在后台静默防抖监听文件变动，随时待命。
* **索引快照与极速秒开:** 当您真正完全退出程序时，系统会自动在本地生成一份轻量级的 `.pkl` 索引快照。下次启动程序时，将直接唤醒快照数据，跳过漫长的扫盘过程，实现真正的“秒开”。

## 🛠️ 开发者工程结构 (企业级 MVC 架构)

```text
Super_Search/
├── assets/                    # 静态资源目录 (应用图标、演示图片)
├── src/                       # 核心源代码目录
│   ├── __init__.py            # 源码包初始化声明
│   ├── main.py                # 程序的唯一主入口
│   ├── config.py              # 全局配置中心 (常量、字典翻译、路径定义)
│   ├── core/                  # 核心业务逻辑层 (Model/Controller)
│   │   ├── __init__.py        # 核心模块导出接口
│   │   ├── engine.py          # 核心搜索与内存索引引擎
│   │   ├── recycle_bin.py     # 底层回收站 COM 接口深度操作封装
│   │   └── watcher.py         # Watchdog 目录实时无感监控模块
│   ├── ui/                    # 用户界面层 (彻底解耦的 View)
│   │   ├── __init__.py        # UI 模块导出接口
│   │   ├── main_window.py     # 主界面布局与回调事件绑定
│   │   └── tray_icon.py       # 系统托盘图标与后台静默挂机管理
│   └── utils/                 # 通用工具层 (纯净辅助模块)
│       ├── __init__.py        # 工具模块导出接口
│       ├── helpers.py         # 路径解析、容量格式化等纯函数
│       └── icons.py           # 内存图标动态生成与管理器
├── tests/                     # 自动化测试用例目录
│   └── test_engine.py         # 核心搜索逻辑的单元测试
├── .gitignore                 # Git 忽略文件配置
├── build.py                   # PyInstaller 一键企业级打包脚本
├── LICENSE                    # GPL 3.0 开源协议
├── README.md                  # 项目说明文档
└── requirements.txt           # Python 依赖清单
```

## 🚀 开发者快速开始

**1. 环境准备**
本项目专为 Windows 平台设计，请确保您的电脑已安装 Python 3.8 或更高版本。

**2. 克隆仓库与安装依赖**
```bash
git clone [https://github.com/LuckyBoy9533/Super_Search.git](https://github.com/LuckyBoy9533/Super_Search.git)
cd Super_Search
pip install -r requirements.txt
```

**3. 运行或编译**
```bash
# 直接运行源码
python src/main.py

# 一键编译企业级独立可执行程序 (.exe)
python build.py
```

## 📚 核心技术栈
* **GUI 框架:** tkinter (包含 ttk 主题扩展)
* **底层 API:** pywin32 (用于调用 Windows Shell 与回收站 COM 接口)
* **文件监控:** watchdog (实现毫秒级的文件系统变动防抖监听)
* **系统托盘:** pystray + Pillow (管理后台挂机与任务栏图标)
* **打包构建:** PyInstaller (自定义高度优化的静态打包脚本)

## 📄 开源协议
本项目采用 GPL 3.0 License 开源协议。
版权所有 (c) 2026 Barry Allen 
如需商业用途，请联系: zhang5626833@gmail.com

---

# Super Search (Lightning-Fast Local Search Tool)
   
Super Search is a lightning-fast local file retrieval tool developed in Python for Windows. Designed to provide a millisecond-level search experience similar to "Everything," it not only features blazing-fast file searching capabilities but also deeply integrates with Windows underlying APIs to support comprehensive Recycle Bin management, real-time unobtrusive file system monitoring, and complete multi-language support.

## ⬇️ Download & Install

🚀 **Click here to download the latest Windows .zip version (Out-of-the-box!)**

1. Go to the Releases page.
2. Download the latest `Super_Search_vX.X.X_Windows.zip` file.
3. Extract the ZIP file to your preferred location.
4. Double-click `SuperSearch.exe` to run. No installation required!

## ✨ Core Features

* **⚡ Lightning-Fast Loading & Retrieval:** Utilizes a memory-based dictionary (Dict) for O(1) complexity deduplication and retrieval. Combined with local snapshot caching (.pkl), it achieves instant application startup.
* **♻️ Deep Recycle Bin Integration:** Eliminates the blind spots of conventional search software by deeply integrating with Windows COM interfaces. It allows you to directly view, restore, and permanently shred Recycle Bin files from the search results, or even empty the Recycle Bin with one click.
* **👀 Real-Time Directory Monitoring:** Powered by the watchdog engine, it monitors local file creations, deletions, and movements (e.g., on the Desktop) in real-time, enabling hot updates of index data and silent debounced refreshing.
* **🌍 Internationalization (i18n) Support:** A built-in multi-language architecture allows seamless, real-time one-click switching between "English" and "简体中文" (Simplified Chinese), covering all UI elements, context menus, and status prompts.
* **🗂️ Smart Categorization & Filtering:** Built-in rich format dictionaries allow one-click categorization and retrieval of images, videos, audio, documents, archives, and code files.
* **💻 Unobtrusive Background Experience:** Integrates pystray to support one-click minimization to the system tray. It runs silently in the background without interrupting your workflow and can be awakened at any time.

## 📸 Interface Preview & Usage Guide

This tool features an out-of-the-box design concept, providing a lightning-fast search experience without complex configurations.

> **💡 Highly Recommended: The program now automatically requests [Administrator] privileges on launch.** > Due to Windows permission isolation mechanisms, running as an administrator maximizes the traversal of the underlying directory structure. According to our benchmark testing, administrator mode can scan nearly 80,000 additional deep or system-level files, ensuring your search has absolutely "no blind spots."

*(Comparison: Standard User Scan vs. Administrator Scan)*

### 🛠️ Project Structure (Enterprise-Grade MVC Architecture)

```text
Super_Search/
├── assets/                    # Static resources (application icons, preview images)
├── src/                       # Core source code directory
│   ├── __init__.py            # Package initialization
│   ├── main.py                # Main application entry point
│   ├── config.py              # Global configurations, constants, and i18n dictionaries
│   ├── core/                  # Core business logic & OS APIs (Model/Controller)
│   │   ├── __init__.py        # Core module exports
│   │   ├── engine.py          # Search engine and in-memory indexer
│   │   ├── recycle_bin.py     # Deep Windows COM interface operations
│   │   └── watcher.py         # Real-time directory monitoring module
│   ├── ui/                    # User interface layer (Decoupled View)
│   │   ├── __init__.py        # UI module exports
│   │   ├── main_window.py     # Main GUI layout and event binding
│   │   └── tray_icon.py       # System tray and background management
│   └── utils/                 # Shared utilities and helpers
│       ├── __init__.py        # Utility module exports
│       ├── helpers.py         # Pure functions for path and size formatting
│       └── icons.py           # Dynamic icon generation and caching
├── tests/                     # Automated testing suite
│   └── test_engine.py         # Unit tests for the core search engine
├── .gitignore                 # Git ignore rules
├── build.py                   # Automated PyInstaller build script
├── LICENSE                    # GPL 3.0 Open Source License
├── README.md                  # Project documentation
└── requirements.txt           # Python dependency list
```

## 🚀 Quick Start (For Developers)

**1. Prerequisites**
This project is exclusively designed for the Windows platform. Please ensure you have Python 3.8 or higher installed on your computer.

**2. Clone the Repository & Install Dependencies**
```bash
git clone [https://github.com/LuckyBoy9533/Super_Search.git](https://github.com/LuckyBoy9533/Super_Search.git)
cd Super_Search
pip install -r requirements.txt
```

**3. Run or Build**
```bash
# Run the source code directly
python src/main.py

# Or build the enterprise-grade executable
python build.py
```

## 📄 License
This project is licensed under the GPL 3.0 License.
Copyright (c) 2026 Barry Allen 
For commercial inquiries, please contact: zhang5626833@gmail.com