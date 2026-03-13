
# src/ui/locales.py

# 语言包字典
LANGUAGE_NAMES = {
    "zh": "简体中文",
    "en": "English"
}

LANGUAGES = {
    "en": {
        # 界面基础
        "title": "Super Search",
        "search_label": "Search Filename:",
        "filter_label": "Filter:",
        "language_label": "Language:",
        "ready_status": "Ready",

        # 状态栏
        "waking_cache_status": "Waking cache...",
        "instant_finish_status": "Instant finish! Loaded {total} historical items",
        "scan_progress_status": "Scanning ({count} items)... Current: {current_dir}",
        "scan_complete_status": "Load complete! Total {total_count} items",
        "found_objects_status": "Found {match_count} objects{limit_tip}",
        "path_copied_status": "Path copied",
        "saving_snapshot_status": "Saving snapshot, please wait...",

        # 列表表头
        "tree_col_icon": "Icon",
        "tree_col_name": "Name",
        "tree_col_path": "Path",
        "tree_col_size": "Size",
        "tree_col_mtime": "Modified Time",
        "unknown_time": "Unknown",

        # 右键菜单
        "restore_action": "♻️ Restore selected {count} files",
        "restore_and_open_action": "📂 Restore and open this file",
        "permanently_delete_action": "❌ Permanently delete selected {count} items",
        "empty_recycle_bin_action": "🗑️ Empty entire Recycle Bin",
        "open_file_action": "Open (File/Folder)",
        "open_folder_action": "Open location (and select)",
        "copy_path_action": "📋 Copy file path",
        "move_to_recycle_bin_action": "🗑️ Move to Recycle Bin ({count} items)",

        # 弹窗消息
        "error_title": "Error",
        "move_to_recycle_bin_confirm": "Are you sure you want to move these {count} items to the Recycle Bin?",
        "permanently_delete_warning": "【DANGEROUS OPERATION】\nAre you sure you want to permanently shred these {count} files?",
        "empty_recycle_bin_warning": "【DESTRUCTIVE OPERATION】\nAre you sure you want to empty the entire Recycle Bin?",
        "empty_recycle_bin_success": "The system Recycle Bin has been completely emptied!",
        "exit_prompt_title": "Exit Confirmation",
        "exit_prompt_message": "Click [Yes] to exit directly\nClick [No] to minimize to system tray\nClick [Cancel] to return",

        # 系统托盘
        "tray_show": "Show Panel",
        "tray_quit": "Full Quit",

        # 【新增】文件分类
        "category_all": "All",
        "category_audio": "Audio",
        "category_video": "Video",
        "category_image": "Image",
        "category_document": "Document",
        "category_archive": "Archive",
        "category_code": "Code",
        "category_folder": "Folder",
        "category_recycle_bin": "Recycle Bin"
    },
    "zh": {
        # 界面基础
        "title": "Super Search (极速搜索)",
        "search_label": "搜索文件名:",
        "filter_label": "筛选:",
        "language_label": "语言:",
        "ready_status": "准备就绪",

        # 状态栏
        "waking_cache_status": "正在唤醒缓存...",
        "instant_finish_status": "秒开完成！已加载 {total} 个历史项目",
        "scan_progress_status": "扫描中 ({count} 项) ... 当前: {current_dir}",
        "scan_complete_status": "加载完成！共 {total_count} 个项目",
        "found_objects_status": "找到 {match_count} 个对象{limit_tip}",
        "path_copied_status": "已复制路径",
        "saving_snapshot_status": "正在保存快照，请稍候...",

        # 列表表头
        "tree_col_icon": "图标",
        "tree_col_name": "名称",
        "tree_col_path": "路径",
        "tree_col_size": "大小",
        "tree_col_mtime": "修改时间",
        "unknown_time": "未知",

        # 右键菜单
        "restore_action": "♻️ 还原选中的 {count} 个文件",
        "restore_and_open_action": "📂 还原并打开此文件",
        "permanently_delete_action": "❌ 彻底删除选定的 {count} 个项目",
        "empty_recycle_bin_action": "🗑️ 清空整个回收站",
        "open_file_action": "打开 (文件/文件夹)",
        "open_folder_action": "打开所在位置 (并选中)",
        "copy_path_action": "📋 复制文件路径",
        "move_to_recycle_bin_action": "🗑️ 移动到回收站 ({count} 项)",

        # 弹窗消息
        "error_title": "错误",
        "move_to_recycle_bin_confirm": "确定要把这 {count} 个项目移到回收站吗？",
        "permanently_delete_warning": "【危险操作】\n确定要彻底粉碎这 {count} 个文件吗？",
        "empty_recycle_bin_warning": "【毁灭级操作】\n确定要清空回收站里的所有文件吗？",
        "empty_recycle_bin_success": "系统回收站已彻底清空！",
        "exit_prompt_title": "退出提示",
        "exit_prompt_message": "点击【是】直接退出\n点击【否】最小化到系统托盘\n点击【取消】返回",

        # 系统托盘
        "tray_show": "显示面板",
        "tray_quit": "完全退出",

        # 【新增】文件分类
        "category_all": "所有",
        "category_audio": "音频",
        "category_video": "视频",
        "category_image": "图片",
        "category_document": "文档",
        "category_archive": "压缩文件",
        "category_code": "代码",
        "category_folder": "文件夹",
        "category_recycle_bin": "回收站"
    }
}

# 全局变量，用于存储当前语言
current_lang = "zh"  # 默认中文


def set_language(lang_code):
    """设置当前语言"""
    global current_lang
    if lang_code in LANGUAGES:
        current_lang = lang_code

def get_text(key, **kwargs):
    """获取当前语言的文本，支持格式化"""
    return LANGUAGES[current_lang].get(key, key).format(**kwargs)
