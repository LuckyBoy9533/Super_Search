# tests/test_engine.py
import unittest
import sys
import os

# 将 src 目录临时加入系统路径，以便测试脚本能顺利导入我们的核心模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from core.engine import SearchEngine


class TestSearchEngine(unittest.TestCase):
    """
    SearchEngine 的自动化单元测试。
    在企业级 CI/CD 流程中，每次提交代码都会自动运行这些测试。
    """

    def setUp(self):
        """
        测试脚手架：在每个测试用例运行前，初始化一个干净的引擎，
        并手动注入一些模拟数据（Mock Data），无需真正去扫盘。
        """
        self.engine = SearchEngine()

        # 模拟字典数据结构: { path_key: (name_lower, orig_name, ext, path, icon_key, size, mtime, is_deleted) }
        self.engine.file_index_dict = {
            r"c:\work\project\main.py": (
            "main.py", "main.py", ".py", r"c:\work\project\main.py", "code", 1024, 1600000000.0, False),
            r"c:\work\docs\readme.md": (
            "readme.md", "README.md", ".md", r"c:\work\docs\readme.md", "doc", 2048, 1600000000.0, False),
            r"d:\movies\matrix.mp4": (
            "matrix.mp4", "Matrix.mp4", ".mp4", r"d:\movies\matrix.mp4", "video", 1024000, 1600000000.0, False),
            r"c:\trash\old_config.json": (
            "old_config.json", "old_config.json", ".json", r"c:\trash\old_config.json", "recycle", 512, 1600000000.0,
            True)
        }

    def test_perform_search_keyword(self):
        """测试基础的关键词匹配是否精准"""
        results, count = self.engine.perform_search("readme", "所有")

        self.assertEqual(count, 1, "应该只找到 1 个匹配项")
        self.assertEqual(results[0][1], "README.md", "原文件名大小写应保留")

    def test_perform_search_filter_code(self):
        """测试代码分类筛选功能"""
        # 注意：这里的 "代码" 必须和 config.py 中的 FILE_CATEGORIES 键名一致
        results, count = self.engine.perform_search("", "代码")

        self.assertEqual(count, 1)
        self.assertEqual(results[0][2], ".py", "筛选出的应该是 .py 后缀的代码文件")

    def test_perform_search_recycle_bin(self):
        """测试回收站专属过滤逻辑"""
        results, count = self.engine.perform_search("", "🗑️ 回收站")

        self.assertEqual(count, 1)
        self.assertTrue(results[0][7], "筛选出的文件 is_deleted 状态必须为 True")

    def test_sync_index_hot_reload_delete(self):
        """测试 Watchdog 传来的删除事件是否能正确 O(1) 抹除内存记录"""
        target_path = r"c:\work\project\main.py"

        # 确保一开始文件在索引里
        self.assertIn(target_path, self.engine.file_index_dict)

        # 模拟触发删除热更新
        self.engine.sync_index_hot_reload(target_path, "deleted")

        # 验证是否被瞬间移除
        self.assertNotIn(target_path, self.engine.file_index_dict, "接收到删除指令后，内存字典中应被移除")


if __name__ == '__main__':
    unittest.main()