# 正式回归只从安装包读取区域资源，不依赖本机制作归档。
from importlib.resources import files
# 每个异常样本使用独立副本，不改写正式JSON。
from copy import deepcopy
# JSON序列化只用于构造检查器的测试blob。
import json
# 正式测试不启动设备。
import unittest
# 清单组合和区域归属是公开装载边界。
from time_maze.adapters.area_loader import AREA_FILES, assemble_level
# 严格文本解析与真实默认装载共用公开接口。
from time_maze.adapters.content_loader import decode_json, load_content
# 整图校验不依赖磁盘或设备。
from time_maze.model.level_validation import parse_level, parse_rules
# 结构检查只消费传入文本，不执行索引源码。
from support.tools.area_structure_check import check_area_structure
# 导出范围必须逐项允许七区资源。
from support.tools.project_files import DATA_FILES, is_allowed_path

# 验证七区文件隔离的正常装载与真实失败边界。
class TestAreaLoading(unittest.TestCase):
    # 所有样本均来自当前安装包，wheel回归也能运行。
    def setUp(self) -> None:
        # 正式JSON集合固定，不能扫描制作目录。
        self.resources = {name.removeprefix("time_maze/data/"): decode_json(files("time_maze").joinpath(name.removeprefix("time_maze/")).read_text(encoding="utf-8"))
                          # 从精确正式集合读取安装资源。
                          for name in DATA_FILES}

    # 测试读取能力模拟包资源缺失，保留清楚的文件失败。
    def read_resource(self, name: str) -> object:
        # 缺文件必须失败，不能回退归档或内嵌旧数据。
        if name not in self.resources:
            # 与实际包资源读取的缺文件类型一致。
            raise FileNotFoundError(name)
        # 返回本测试副本，不持有全局共享可变对象。
        return self.resources[name]

    # 组合输入经过纯整图校验，所有测试使用同一公开路径。
    def parse_resources(self, manifest: object):
        # 地图谱箱引用必须使用实际规则。
        rules = parse_rules(self.resources["rules.json"])
        # 不只验证引用字符串，还核验全图连接和落脚。
        return parse_level(assemble_level(manifest, self.read_resource), rules)

    # 七张文件按清单组合与默认游戏实际装载得到同一冻结定义。
    def test_seven_installed_areas_match_default_game(self) -> None:
        # 不在安装副本中读取工作区JSON。
        level, _, _ = load_content()
        # 清单准确七区且不再存放完整布局。
        self.assertNotIn("rooms", self.resources["level.json"])
        # 独立组合产生与正式应用完全相同的定义。
        self.assertEqual(self.parse_resources(self.resources["level.json"]), level)
        # 每区资源逐项进入精确导出边界。
        for _, name in AREA_FILES:
            # 真正允许的是当前单区文件。
            self.assertTrue(is_allowed_path(f"time_maze/data/{name}"))
        # 区域目录存在不意味着新素材被整体放行。
        self.assertFalse(is_allowed_path("time_maze/data/areas/private_layout.json"))

    # 缺区、重复和错配路径必须在启动时拒绝。
    def test_invalid_manifest_references(self) -> None:
        # 每个样本独立，互相不能污染。
        for failure in ("missing", "duplicate", "wrong_file", "escape", "embedded"):
            # 保存子样本名称供失败定位。
            with self.subTest(failure=failure):
                # 原始清单保持不变。
                manifest = deepcopy(self.resources["level.json"])
                # 缺区不能运行成局部地图。
                if failure == "missing":
                    # 删除最后一区引用模拟打包或配置遗漏。
                    manifest["areas"].pop()
                # 重复引用不能以覆盖方式隐藏另一缺区。
                elif failure == "duplicate":
                    # 用A重复占用G位置。
                    manifest["areas"][-1] = manifest["areas"][0]
                # 文件名须与当前ID真实归属一致。
                elif failure == "wrong_file":
                    # A引用B文件属于错配。
                    manifest["areas"][0]["file"] = AREA_FILES[1][1]
                # 清单不能越过正式包目录。
                elif failure == "escape":
                    # 路径逃逸在调用读取能力前就必须失败。
                    manifest["areas"][0]["file"] = "../support/production/layout.json"
                # 不允许并列保存第二份当前布局。
                else:
                    # 旧集中字段不能重新加入清单。
                    manifest["rooms"] = []
                # 所有错误都属于明确配置失败。
                with self.assertRaises(ValueError):
                    # 通过实际公开组合边界验证。
                    self.parse_resources(manifest)

    # 缺区域文件不能暗中从旧集中数据恢复。
    def test_missing_area_file_fails(self) -> None:
        # 删除B实际布局，清单引用仍存在。
        del self.resources[AREA_FILES[1][1]]
        # 文件读取失败保留给启动边界。
        with self.assertRaises(FileNotFoundError):
            # 使用完整清单请求缺失文件。
            self.parse_resources(self.resources["level.json"])

    # 文件正文ID必须和清单一致。
    def test_wrong_area_body_id_fails(self) -> None:
        # 只改变G文件正文的实际ID。
        self.resources[AREA_FILES[-1][1]]["room"]["id"] = "A"
        # 不能通过清单强行覆盖正文错配。
        with self.assertRaises(ValueError):
            # 实际启动组合边界应拒绝。
            self.parse_resources(self.resources["level.json"])

    # 独立文件中的跨区目标错误仍须由整图校验发现。
    def test_cross_area_destination_is_validated(self) -> None:
        # A的实际门引用是测试目标。
        room = self.resources[AREA_FILES[0][1]]["room"]
        # 目标区域不存在时即使七区文件齐全也不能运行。
        room["portals"][0]["target_region"] = "Z"
        # 组合地图必须整体失败。
        with self.assertRaises(ValueError):
            # 整图校验不能因为文件隔离被跳过。
            self.parse_resources(self.resources["level.json"])

    # 索引数据结构检查拒绝缺文件、额外布局和安装声明遗漏。
    def test_blob_structure_and_package_boundaries(self) -> None:
        # 安装包资源构造只读检查样本，不访问真实索引。
        blobs = {f"time_maze/data/{name}": (json.dumps(value) + "\n").encode("utf-8")
                 # 数据样本全部来自当前正式安装资源。
                 for name, value in self.resources.items()}
        # 精确包资源声明用TOML数组表达。
        declared = sorted(name.removeprefix("time_maze/") for name in DATA_FILES)
        # 这是配置样本，不是被执行的源码。
        blobs["pyproject.toml"] = ("[tool.setuptools.package-data]\ntime_maze = " + json.dumps(declared) + "\n").encode("utf-8")
        # 每项正式资源分别开放，目录不整体放行。
        blobs[".gitignore"] = ("\n".join(f"!/{name}" for name in sorted(DATA_FILES)) + "\n").encode("utf-8")
        # 合法结构应通过真实检查器。
        self.assertEqual(check_area_structure(blobs), [])
        # 缺文件不能被工作区中存在的资源掩盖。
        missing = dict(blobs)
        # 删除F文件模拟不完整索引。
        del missing[f"time_maze/data/{AREA_FILES[5][1]}"]
        # 检查只消费传入样本，必须实际失败。
        self.assertTrue(check_area_structure(missing))
        # 额外布局不自动允许成为第二份来源。
        extra = dict(blobs)
        # 未声明JSON不能借已开放目录进入正式范围。
        extra["time_maze/data/areas/old_g.json"] = b"{}"
        # 结构检查应指出多出的资源。
        self.assertTrue(check_area_structure(extra))
        # 包数据声明遗漏即使运行源码可玩也须失败。
        incomplete_package = dict(blobs)
        # 仅保留清单而省略七区实际文件。
        incomplete_package["pyproject.toml"] = b'[tool.setuptools.package-data]\ntime_maze = ["data/level.json"]\n'
        # 不把源码可玩误判为安装包完整。
        self.assertTrue(check_area_structure(incomplete_package))

    # 严格解析不能让重复字段或非有限值在索引检查中静默覆盖。
    def test_strict_json_text(self) -> None:
        # 样本分别模拟重复版本与非标准数字。
        for source in ('{"schema_version": 1, "schema_version": 2}', '{"value": NaN}'):
            # 明确报错而不是采用最后一项。
            with self.assertRaises(ValueError):
                # 包装载与blob检查使用同一公开解析器。
                decode_json(source)
