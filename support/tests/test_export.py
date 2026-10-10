# 临时目录模拟导出边界，不读取真实私人素材。
import tempfile
# 路径对象用于建立临时正式树与制作区。
from pathlib import Path
# 正式辅助测试不进入运行包。
import unittest
# 独立导出工具只按精确允许集合复制。
from support.tools.export_game import copy_snapshot
# 索引和源码导出共用这一明确允许集合。
from support.tools.project_files import is_allowed_path

# 验证正式文件名不能通过符号链接把制作正文带入产物。
class TestExport(unittest.TestCase):
    # 未审阅新稿和路径逃逸不能借技术后缀进入正式范围。
    def test_exact_document_allowlist(self) -> None:
        # 正式技术文档名已逐项声明。
        self.assertTrue(is_allowed_path("support/technical/requirements.md"))
        # 未审阅稿、视频区和依赖旧入口分别拒绝。
        for name in ("support/technical/unreviewed_notes.md", "support/standards/unreviewed_notes.md",
                     # 父目录逃逸与绝对路径不是正式相对文件名。
                     "support/production/draft.py", "time_maze/../support/production/draft.py",
                     # 未使用的根依赖文件不预先开放。
                     "/time_maze/main.py", "requirements.txt", "requirements-dev.txt"):
            # 测试使用真实路径规则，不自行模拟被测集合。
            self.assertFalse(is_allowed_path(name))

    # 根入口链接与普通正式文件应有不同导出结果。
    def test_root_symlink_does_not_copy_private_content(self) -> None:
        # 测试结束后自动移除所有临时模拟资料。
        with tempfile.TemporaryDirectory(prefix="time-maze-export-test-") as directory:
            # 源与目标不使用真实制作目录。
            root = Path(directory) / "source"
            # 私有正文只是测试哨兵。
            private = root / "support/production/draft.py"
            # 创建模拟制作层级。
            private.parent.mkdir(parents=True)
            # 哨兵不是正式产品数据。
            private.write_text("private_production_sentinel\n", encoding="utf-8")
            # 允许文件名不改变链接实际来源的私有性质。
            (root / "main.py").symlink_to(private)
            # 普通声明文件是可复制的对照。
            (root / "requirements.lock").write_text("pygame-ce==2.5.8\n", encoding="utf-8")
            # 快照只接受正式普通文件。
            destination = Path(directory) / "snapshot"
            # 调用正式导出边界，不自己筛选被测路径。
            names = copy_snapshot(root, destination)
            # 真实普通依赖声明仍保留。
            self.assertEqual(names, ("requirements.lock",))
            # 私人正文不能借正式入口名进入快照。
            self.assertFalse((destination / "main.py").exists())
            # 制作目录整体不进入快照。
            self.assertFalse((destination / "support/production").exists())
