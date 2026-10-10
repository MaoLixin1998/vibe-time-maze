# 读取能力显式传入，组合逻辑不自行搜索目录或制作素材。
from collections.abc import Callable
# 格式与标识复用正式边界校验，完整拓扑仍交给parse_level。
from time_maze.model.level_validation import require_mapping, require_list, require_integer

# 本作七个正式区域有明确资源归属；工具同向引用，不反向侵入主体。
AREA_FILES = (
    # 剑台室与迷宫岔路各自只维护本区布局。
    ("A", "areas/a_sword_chamber.json"), ("B", "areas/b_maze_crossroads.json"),
    # 货运回廊和夜闸的连接条件留在各区定义。
    ("C", "areas/c_cargo_corridor.json"), ("D", "areas/d_night_gate.json"),
    # 鸡领地、巢后通道和奖励台地是独立资源。
    ("E", "areas/e_chicken_yard.json"), ("F", "areas/f_nest_passage.json"),
    # G只保存本区布局，不混入视频演出数据。
    ("G", "areas/g_meadow.json"),
)

# 将磁盘清单v2组合为既有纯模型v1输入，模型公开定义和一局状态不变。
def assemble_level(manifest: object, read_resource: Callable[[str], object]) -> dict:
    # 清单只接受全图配置和区域引用，禁止重新内嵌rooms。
    data = require_mapping(manifest, {"schema_version", "initial_region", "initial_position",
                                      "chicken_spawns", "areas"})
    # 磁盘清单格式升级不改变内存模型格式。
    require_integer(data["schema_version"], 2, 2)
    # 七区必须全部列出，每个引用还需核验实际归属。
    entries = require_list(data["areas"], 7)
    # 明确固定集合阻止重复、遗漏和../等资源逃逸。
    expected = dict(AREA_FILES)
    # 已加载ID独立记录，不让重复引用覆盖前一布局。
    seen = set()
    # 原数组顺序保留到正式冻结模型。
    rooms = []
    # 每区只有一处实际布局来源。
    for value in entries:
        # ID和资源名是清单的全部单区字段。
        entry = require_mapping(value, {"id", "file"})
        # 明确类型后才能安全查询，不接受列表等非标识对象。
        if type(entry["id"]) is not str or type(entry["file"]) is not str:
            # 数据错误在启动边界报告。
            raise ValueError("区域引用必须为字符串")
        # 文件必须属于当前ID，路径不可任意展开。
        if entry["id"] in seen or expected.get(entry["id"]) != entry["file"]:
            # 错配、重复及未知文件均不能进入模型。
            raise ValueError(f"区域引用重复或归属错误: {entry['id']}")
        # 标记已占用的区域ID。
        seen.add(entry["id"])
        # 仅通过注入读取能力读取准确的正式包资源。
        area = require_mapping(read_resource(entry["file"]), {"schema_version", "room"})
        # 每区文件版本独立于全图清单。
        require_integer(area["schema_version"], 1, 1)
        # 实际布局ID必须与引用一致，其他字段随后由整图解析严格校验。
        if type(area["room"]) is not dict or area["room"].get("id") != entry["id"]:
            # 不通过清单ID强行覆盖错误的布局。
            raise ValueError(f"区域文件ID不匹配: {entry['file']}")
        # 合法原始布局保留全部值，不复制或改写门条件。
        rooms.append(area["room"])
    # 缺区和空清单不能运行成不完整地图。
    if seen != expected.keys():
        # 完整主线需要七区同时装载。
        raise ValueError("区域清单必须完整包含A—G")
    # 原有纯模型解析仍负责全部跨区目标、落脚与物件引用。
    return {"schema_version": 1, "initial_region": data["initial_region"],
            # 初始坐标与鸡出生点属于全图配置。
            "initial_position": data["initial_position"], "chicken_spawns": data["chicken_spawns"],
            # 所有独立布局一起冻结和校验。
            "rooms": rooms}
