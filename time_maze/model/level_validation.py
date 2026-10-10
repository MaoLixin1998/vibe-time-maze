# 有限性校验拒绝NaN和无穷行为时间。
from math import isfinite
# 稳定ID只允许明确英文标识，避免显示文字参与规则。
from re import fullmatch
# 纯数据定义逐类导入，不依赖JSON或磁盘。
from time_maze.model.interactive_object import InteractiveObject
# 门槛定义独立于实际开闭状态。
from time_maze.model.portal_definition import PortalDefinition
# 房间保存冻结后的静态地形。
from time_maze.model.room_definition import RoomDefinition
# 地图聚合所有已校验房间。
from time_maze.model.level_definition import LevelDefinition
# 曲谱与输入匹配使用同一表示。
from time_maze.model.melody_definition import MelodyDefinition
# 行为参数统一冻结注入。
from time_maze.model.rules_definition import RulesDefinition
# 七音事件边界与实际演奏共用同一校验。
from time_maze.model.keyboard_rules import validate_notes

# 数值先转换为可表示有限浮点，所有公开秒数与进度共用实际边界。
def require_finite_number(value: object) -> float:
    # 不接受bool、字符串或其他可隐式转换对象。
    if type(value) not in (int, float):
        # 类型错误统一表达为输入契约失败。
        raise ValueError("数值必须为真实int或float")
    # 巨量整数转浮点可能溢出，转换失败不能泄露为设备或帧循环异常。
    try:
        # 模拟统一使用浮点秒数及归一化进度。
        number = float(value)
    # 只处理明确的表示范围溢出，不吞掉其他实现错误。
    except OverflowError as error:
        # 保留原始原因链，同时维持公开ValueError契约。
        raise ValueError("数值超出有限浮点表示范围") from error
    # NaN、正无穷和负无穷都不属于可模拟输入。
    if not isfinite(number):
        # 不通过夹紧或回退成零掩盖无效值。
        raise ValueError("数值必须有限")
    # 只有实际合法数值才返回给状态变更。
    return number

# 字典必须有准确字段，避免拼写错后静默采用默认值。
def require_mapping(value: object, required: set[str], optional: set[str] | None = None) -> dict:
    # bool、列表和自定义映射不视为JSON对象。
    if type(value) is not dict:
        # 外部输入类型问题保留明确原因。
        raise ValueError("配置字段必须为对象")
    # 只允许本版契约声明的字段。
    allowed = required | (optional or set())
    # 缺少必要字段或意外字段都拒绝。
    if not required <= value.keys() or not value.keys() <= allowed:
        # 列出实际键以定位格式版本问题。
        raise ValueError(f"配置字段不匹配: {sorted(value)}")
    # 原始字典只在适配校验期间使用，不导出给模型。
    return value

# 列表长度在解析前限定，防止意外巨量配置。
def require_list(value: object, limit: int = 2048) -> list:
    # JSON数组必须为真实列表。
    if type(value) is not list or len(value) > limit:
        # 不把字符串当作字符数组处理。
        raise ValueError("配置数组类型或长度非法")
    # 调用者随后逐项冻结。
    return value

# 字符串必须非空且保持合理显示与ID长度。
def require_text(value: object, limit: int = 160) -> str:
    # 不通过str()掩盖非法配置类型。
    if type(value) is not str or not value or len(value) > limit:
        # 文本不是业务默认值入口。
        raise ValueError("配置文字类型或长度非法")
    # 返回原UTF-8解码后的字符串。
    return value

# 稳定ID与中文展示名称分离。
def require_id(value: object) -> str:
    # 先校验真实字符串。
    text = require_text(value, 64)
    # ID只允许字母开头的英文、数字及下划线。
    if fullmatch(r"[A-Za-z][A-Za-z0-9_]*", text) is None:
        # 错误ID不能作为另一有效ID回退。
        raise ValueError(f"非法稳定ID: {text}")
    # 返回已校验ID。
    return text

# 整数范围检查明确拒绝bool。
def require_integer(value: object, minimum: int, maximum: int) -> int:
    # type而非isinstance避免True混成一格或一个音。
    if type(value) is not int or not minimum <= value <= maximum:
        # 格数与输入上限不做自动取整。
        raise ValueError("配置整数越界或类型非法")
    # 返回精确整数。
    return value

# 坐标必须为两个真实整数，边界在房间层继续检查。
def require_position(value: object) -> tuple[int, int]:
    # JSON坐标使用明确二项数组。
    parts = require_list(value, 2)
    # 缺少项同样不合法。
    if len(parts) != 2:
        # 不自行补零坐标。
        raise ValueError("坐标必须为两项")
    # 最大尺寸由后续房间网格限定。
    return tuple(require_integer(part, 0, 127) for part in parts)

# 时长参数必须有限、为秒并处于玩法可控范围。
def require_seconds(value: object, minimum: float = 0.04, maximum: float = 30.0) -> float:
    # 统一拒绝bool、非有限值和巨大整数表示溢出。
    seconds = require_finite_number(value)
    # 正式时长还必须位于所属玩法的有限秒数区间。
    if not minimum <= seconds <= maximum:
        # 负数、零与无限时间都不是有效动画。
        raise ValueError("配置秒数越界、非有限或类型非法")
    # 模型统一以浮点秒数进行时间步运算。
    return seconds

# 校验并冻结音符、效果、计时与前缀限制。
def parse_rules(raw: object) -> RulesDefinition:
    # 必要字段固定本版规则契约。
    data = require_mapping(raw, {"schema_version", "melodies", "movement_seconds", "warning_seconds",
                                # 追逐与返巢使用独立参数。
                                "chicken_step_seconds", "return_step_seconds", "exit_seconds", "max_notes"},
                           # 新动画时长可采用正式默认值。
                           {"box_seconds", "slide_seconds"})
    # 本版不猜测其他schema的字段含义。
    if require_integer(data["schema_version"], 1, 1) != 1:
        # 保留显式版本失败。
        raise ValueError("规则版本非法")
    # 输入上限必须覆盖所有已定义曲谱。
    max_notes = require_integer(data["max_notes"], 1, 64)
    # 唯一性检查只在解析过程持有可变容器。
    melodies = []
    # 同一曲谱ID不得覆盖此前定义。
    identifiers = set()
    # 每个已选曲谱独立冻结。
    for entry in require_list(data["melodies"], 32):
        # 未锁定其他曲目不允许用空序列占位。
        item = require_mapping(entry, {"id", "name", "notes", "effect", "category"})
        # 名称不参与匹配。
        identifier = require_id(item["id"])
        # 重复ID拒绝，不任取最后一个。
        if identifier in identifiers:
            # 输出稳定ID供修复。
            raise ValueError(f"重复曲谱ID: {identifier}")
        # 类型和音区通过正式输入校验。
        notes = validate_notes(tuple(tuple(require_list(note, 2))
                                     # 每音数组必须二项且外层有界。
                                     for note in require_list(item["notes"], max_notes)), max_notes)
        # 空曲谱会把Enter变成意外状态切换，必须拒绝。
        if not notes:
            # 不允许空曲谱效果。
            raise ValueError("曲谱不得为空")
        # 效果只开放真实已经实现的功能。
        if type(item["effect"]) is not str or item["effect"] not in {"toggle_day", "egg_lullaby", "chicken_call"}:
            # 未实现效果不能宣称数据驱动可用。
            raise ValueError("曲谱效果尚未实现或非法")
        # 分类只影响展示及可选标记。
        if type(item["category"]) is not str or item["category"] not in {"main", "optional", "hidden"}:
            # 不默认为主线而泄露隐藏曲谱。
            raise ValueError("曲谱分类非法")
        # 精确重复和跨类前缀歧义都在装载时检查。
        for previous in melodies:
            # 短序列是长序列开头时拒绝，避免提交策略变化后误触。
            shorter = min(len(notes), len(previous.notes))
            # 共有短前缀全部相等属于歧义。
            if notes[:shorter] == previous.notes[:shorter]:
                # 给出冲突曲谱而非含糊通过。
                raise ValueError(f"曲谱重复或前缀歧义: {identifier}/{previous.id}")
        # 冻结序列与显示定义。
        melodies.append(MelodyDefinition(identifier, require_text(item["name"]), notes,
                                          # ID已验证为声明过的稳定效果。
                                          item["effect"], item["category"]))
        # 后续项不能复用同一稳定ID。
        identifiers.add(identifier)
    # 本轮必须有且只有一首原创时间主线。
    if sum(melody.effect == "toggle_day" for melody in melodies) != 1:
        # 不默认填两首昼夜曲或无曲状态。
        raise ValueError("必须定义唯一原创时间曲")
    # 所有数字边界通过后整体创建只读规则。
    return RulesDefinition(tuple(melodies), require_seconds(data["movement_seconds"], 0.04, 2.0),
                           # 警告必须至少2.8秒，不能因配置缩成无反应窗口。
                           require_seconds(data["warning_seconds"], 2.8, 15.0),
                           # 追逐、返巢和出口都是有限正秒数。
                           require_seconds(data["chicken_step_seconds"]),
                           # 返巢可与追逐不同速，但不能瞬移。
                           require_seconds(data["return_step_seconds"]),
                           # 出口过场上限防止永远无法领奖。
                           require_seconds(data["exit_seconds"]), max_notes,
                           # 推箱与滑落使用可替换正式时长。
                           require_seconds(data.get("box_seconds", 1.2)),
                           # 滑落时长与房间数量无关。
                           require_seconds(data.get("slide_seconds", 0.9)))

# 单个房间冻结地形、门、动态物与地标。
def parse_room(raw: object) -> RoomDefinition:
    # 地形与动态对象分别提供。
    data = require_mapping(raw, {"id", "name", "width", "height", "rows", "portals",
                                # 领地不替代实际碰撞地板。
                                "objects", "territory", "landmarks"}, {"pedestal_steps"})
    # 网格尺寸限定，避免误读巨大资源。
    width = require_integer(data["width"], 3, 128)
    # 以格为单位校验地图高度。
    height = require_integer(data["height"], 3, 128)
    # 行文本必须匹配明确网格尺寸。
    rows = require_list(data["rows"], height)
    # 每格只允许墙或地板两个静态符号。
    if len(rows) != height or any(type(row) is not str or len(row) != width or
                                  # 动态箱、鸡、剑都不烘焙进地形字符。
                                  any(symbol not in "#." for symbol in row) for row in rows):
        # 不用补墙掩盖实际缺失地形。
        raise ValueError("地图行宽、高度或静态符号非法")
    # 冻结所有合法地板。
    floors = frozenset((x, y) for y, row in enumerate(rows)
                       # 周边墙也在同一份静态地形中。
                       for x, symbol in enumerate(row) if symbol == ".")
    # 每区必须有真实站立空间。
    if not floors:
        # 不允许空区假装可玩地图。
        raise ValueError("区域缺少地板")
    # 逐个解析门槛定义。
    portals = []
    # 门槛不得互相重叠。
    threshold_positions = set()
    # 数量有界且稳定ID随后全局去重。
    for entry in require_list(data["portals"], 12):
        # 门条件和用途文字分别保存。
        item = require_mapping(entry, {"id", "position", "direction", "target_region",
                                      # 目标格由地图聚合层验证。
                                      "target_position", "condition", "label", "kind"})
        # 门槛格必须属于本房间地板。
        position = require_position(item["position"])
        # 同一点多门会令方向和提示歧义，当前规格不需要。
        if position not in floors or position in threshold_positions:
            # 配置边界错误清晰拒绝。
            raise ValueError("门槛格无地板或重叠")
        # 只接受正式四向输入。
        if type(item["direction"]) is not str or item["direction"] not in {"up", "down", "left", "right"}:
            # 不默认猜方向。
            raise ValueError("门方向非法")
        # 夜间及出口条件是实际已实现集合。
        if type(item["condition"]) is not str or item["condition"] not in {"open", "child", "cargo", "night", "child_day"}:
            # 未知条件不能放行。
            raise ValueError("门条件非法")
        # 普通门、滑落与排水道用明确种类区分。
        if type(item["kind"]) is not str or item["kind"] not in {"door", "slide", "drain", "drain_drop"}:
            # 不伪装支持额外通路机制。
            raise ValueError("门类型非法")
        # 创建冻结门定义。
        portals.append(PortalDefinition(require_id(item["id"]), position, item["direction"],
                                        # 稳定目标与坐标稍后跨房验证。
                                        require_id(item["target_region"]), require_position(item["target_position"]),
                                        # 提示不参与规则计算。
                                        item["condition"], require_text(item["label"]), item["kind"]))
        # 后续门不能复用同一点。
        threshold_positions.add(position)
    # 独立交互物与门不共享可变状态。
    objects = []
    # 同格多件暂不支持，避免邻近操作歧义。
    object_positions = set()
    # 数量在当前七区实际用途内限定。
    for entry in require_list(data["objects"], 32):
        # 只有货箱需要目标格。
        item = require_mapping(entry, {"id", "kind", "position", "payload"}, {"target_position"})
        # 可交互物必须在真实地板上。
        position = require_position(item["position"])
        # 角色不能和未知底图物件发生虚假碰撞。
        if position not in floors or position in object_positions:
            # 不将错误对象坐标移到安全点。
            raise ValueError("物件格无地板或重叠")
        # 当前真实玩法支持这五种对象。
        if type(item["kind"]) is not str or item["kind"] not in {"sword", "cargo_box", "score", "reward", "nest"}:
            # 没有实现的种类不允许载入。
            raise ValueError("物件类型非法")
        # 有货箱目标才解析额外坐标。
        target = require_position(item["target_position"]) if "target_position" in item else None
        # 非货箱不应该携带推物终点。
        if item["kind"] != "cargo_box" and target is not None:
            # 拒绝含义冲突的配置。
            raise ValueError("非货箱不能定义推物终点")
        # 货箱严格向北停入本区合法凹位。
        if item["kind"] == "cargo_box" and (target not in floors or target[0] != position[0] or target[1] >= position[1]):
            # 不接受自由推错或跨区终点。
            raise ValueError("货箱必须向北推入本区合法终点")
        # 空payload合法，不把空字符串误当缺字段。
        if type(item["payload"]) is not str or len(item["payload"]) > 160:
            # 不将任意对象转为字符串。
            raise ValueError("物件内容引用非法")
        # 冻结对象定义。
        objects.append(InteractiveObject(require_id(item["id"]), item["kind"], position,
                                         # 内容引用在聚合层按对象用途验证。
                                         item["payload"], target))
        # 同格定义保持唯一。
        object_positions.add(position)
    # 货箱从初始格到北侧凹位的整段路径必须真实可推。
    for cargo in (item for item in objects if item.kind == "cargo_box"):
        # 已验证同列北向终点，所有经过格包含两个端点。
        push_path = frozenset((cargo.position[0], y)
                              # 北向移动不允许跳过墙或其他占位。
                              for y in range(cargo.target_position[1], cargo.position[1] + 1))
        # 施力者停在初始箱南侧一格，不随箱动画进入通道。
        approach = (cargo.position[0], cargo.position[1] + 1)
        # 路径中每格及施力格都必须有实际地板。
        if not push_path <= floors or approach not in floors:
            # 不把隔墙动画伪装成合法推箱。
            raise ValueError("货箱推物路径或南侧站位缺少地板")
        # 非货箱对象在路径或站位上会形成真实重叠。
        occupied = {item.position for item in objects if item.id != cargo.id}
        # 门槛与推物动画不能共享占格，避免入门撞箱或推入活动门。
        thresholds = {portal.position for portal in portals}
        # 完整路径与施力格都要避开其他实体和门槛。
        if (push_path | {approach}) & (occupied | thresholds):
            # 正式配置不能依赖穿过另一个对象完成动画。
            raise ValueError("货箱路径或南侧站位与交互物或门槛重叠")
        # 指定停位必须是只有一条地板连接的凹位，不能堵在回程主路。
        x, y = cargo.target_position
        # 固定终点的四个邻格只用于静态拓扑检查。
        neighbors = {(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)}
        # 凹位不能成为穿行路口或孤立不可达终点。
        if len(neighbors & floors) != 1:
            # 不允许一个看似可画的停位实际切断通道。
            raise ValueError("货箱终点必须为通路旁单连接凹位")
    # 领地必须来自同一份地板。
    territory_values = [require_position(position) for position in require_list(data["territory"], 16384)]
    # 重复点通常是配置复制错误，不能默默去重。
    if len(territory_values) != len(set(territory_values)) or not set(territory_values) <= floors:
        # 鸡领地不能覆盖不可站立的墙。
        raise ValueError("鸡领地重复或超出地板")
    # 固定地标为轻量位置和文字，不引入通关条件。
    landmarks = []
    # 解析各个静态地标。
    for entry in require_list(data["landmarks"], 64):
        # 地标必须具有x、y和用途文字三项。
        parts = require_list(entry, 3)
        # 列表长度在索引前核验。
        if len(parts) != 3:
            # 不静默省略标签。
            raise ValueError("地标必须为坐标与文字三项")
        # 地标坐标沿用正常格边界。
        position = require_position(parts[:2])
        # 地标只能出现在实际可查看地板上。
        if position not in floors:
            # 防止不可见或墙外提示。
            raise ValueError("地标超出地板")
        # 冻结为三项值。
        landmarks.append((*position, require_text(parts[2])))
    # 三层石座属于静态地形表达，矩形不能侵入可走地板。
    pedestal_steps = []
    # 不需要石台的区域保持空值，避免伪造统一模板。
    for entry in require_list(data.get("pedestal_steps", []), 3):
        # 每层以左上与右下四个整数表达。
        parts = require_list(entry, 4)
        # 四项边界在使用前严格核验。
        if len(parts) != 4 or any(type(value) is not int for value in parts):
            # bool及少项都拒绝。
            raise ValueError("石座层矩形格式非法")
        # 拆分静态矩形边界。
        x1, y1, x2, y2 = parts
        # 矩形必须在本图以内且不覆盖地板。
        if not 0 <= x1 <= x2 < width or not 0 <= y1 <= y2 < height or any((x, y) in floors for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)):
            # 渲染不能借装饰绕过真实碰撞。
            raise ValueError("石座矩形越界或覆盖地板")
        # 单层数据冻结为不可变元组。
        pedestal_steps.append(tuple(parts))
    # 整体房间只含不可变嵌套值。
    return RoomDefinition(require_id(data["id"]), require_text(data["name"]), width, height,
                          # 运行对象共享地形定义而非共享状态。
                          floors, tuple(portals), tuple(objects), frozenset(territory_values), tuple(landmarks),
                          # 三层石座与其碰撞区域共享正式配置。
                          tuple(pedestal_steps))

# 验证跨房引用及所有稳定ID，最后冻结七区地图。
def parse_level(raw: object, rules: RulesDefinition) -> LevelDefinition:
    # 初始格与鸡出生点也属于正式配置。
    data = require_mapping(raw, {"schema_version", "initial_region", "initial_position",
                                # 鸡出生点按巢顺序对应，绝不硬编码剧情站位。
                                "chicken_spawns", "rooms"})
    # 只接受当前schema。
    require_integer(data["schema_version"], 1, 1)
    # 房间解析完成后再验证互相引用。
    rooms = tuple(parse_room(room) for room in require_list(data["rooms"], 7))
    # 本作仅A至G七区，长坡不成为第八区。
    if len(rooms) != 7 or {room.id for room in rooms} != set("ABCDEFG"):
        # 重复房ID也会导致集合数量不符。
        raise ValueError("地图必须恰好包含A至G七区")
    # 局部索引只用于装载校验，不导出可变引用。
    indexed = {room.id: room for room in rooms}
    # 静态地板不表示动态实体可以重叠，推物整段保留为不可跨门落脚区。
    cargo_hazards = {room.id: frozenset((item.position[0], y)
                                       # 只有真实货箱才声明动态路径，包含初始格和终点。
                                       for item in room.objects if item.kind == "cargo_box"
                                       # 避免非货路门把玩家放在未推箱时封闭的箱后空间。
                                       for y in range(item.target_position[1], item.position[1] + 1))
                     # 每区独立危险格，不把C箱错误推广到其他区域。
                     for room in rooms}
    # 全局ID集合防止不同房间覆盖同一领取或门事件。
    identifiers = set()
    # 宝箱内容引用正式曲谱ID。
    score_ids = {melody.id for melody in rules.melodies}
    # 逐房检查真实跨区连接及内容引用。
    for room in rooms:
        # 门和物件ID共同去重，避免UI交互ID碰撞。
        for item in (*room.portals, *room.objects):
            # 全局稳定ID不能重复。
            if item.id in identifiers:
                # 原因带出重复ID。
                raise ValueError(f"重复地图ID: {item.id}")
            # 记录此合法ID。
            identifiers.add(item.id)
        # 目标引用必须指向真实房间地板。
        for portal in room.portals:
            # 确认目标存在后再查询落脚。
            if portal.target_region not in indexed or portal.target_position not in indexed[portal.target_region].floors:
                # 不转移到目标房间的默认点。
                raise ValueError(f"非法跨区落脚: {portal.id}")
            # 来路条件可能允许任一箱状态进入，落脚不得依赖穿进动态重物路径。
            if portal.target_position in cargo_hazards[portal.target_region]:
                # JSON和直接模型构造均在本边界拒绝危险目标。
                raise ValueError(f"跨区落脚与货箱占格或推物路径重叠: {portal.id}")
        # 各谱箱只允许已实现曲谱。
        for item in room.objects:
            # 核心交互能力只放在已确定所属区域，不允许通过外部配置任意移位。
            owners = {"sword": "A", "cargo_box": "C", "score": "B", "reward": "G", "nest": "F"}
            # 年龄只能在A切换，其余对象保持本关卡边界。
            if room.id != owners[item.kind]:
                # 配置不能把奖励或换龄点搬进追逐通道。
                raise ValueError(f"交互物区域不符合关卡职责: {item.id}")
            # 不把漏拼的曲谱ID当作未知隐藏项。
            if item.kind == "score" and item.payload not in score_ids:
                # 给出实际宝箱ID。
                raise ValueError(f"谱箱引用不存在: {item.id}")
    # 固定核心物件数量是当前关卡安全边界。
    kinds = [item.kind for room in rooms for item in room.objects]
    # 两谱箱、唯一货箱及奖励箱不得意外复制。
    if any(kinds.count(kind) != expected for kind, expected in
           # 鸡巢数量与spawn稍后单独对应。
           (("sword", 1), ("cargo_box", 1), ("score", 2), ("reward", 1))):
        # 配置错不能生成双重领奖或额外阻挡。
        raise ValueError("关键交互物数量不符合七区关卡")
    # 初始区域ID与坐标必须在已校验地图内。
    initial_region = require_id(data["initial_region"])
    # 用同一格坐标校验。
    initial_position = require_position(data["initial_position"])
    # 初始状态不落在墙外。
    if initial_region not in indexed or initial_position not in indexed[initial_region].floors:
        # 不用硬编码初始格掩盖错误。
        raise ValueError("初始落脚无效")
    # 正常出生与跨区一样不能把玩家放进任一动态箱状态。
    if initial_position in cargo_hazards[initial_region]:
        # 不从错误出生点自动挪到别处。
        raise ValueError("初始落脚与货箱占格重叠")
    # 正式序章必须从剑台庭开始，其他安全点只由实际检查点保存。
    if initial_region != "A":
        # 配置不能跳过真实首次拔剑流程。
        raise ValueError("正式入口必须位于A剑台庭")
    # 三项鸡节点即区域、x和y。
    spawns = []
    # 出生点有界且与巢数严格对应。
    for entry in require_list(data["chicken_spawns"], 32):
        # 先检查长度，避免非法索引。
        parts = require_list(entry, 3)
        # 缺字段不允许。
        if len(parts) != 3:
            # 输出明确契约要求。
            raise ValueError("鸡出生点必须为区域、x、y")
        # 区域只使用稳定ID。
        region = require_id(parts[0])
        # 坐标使用正常格边界。
        position = require_position(parts[1:])
        # 鸡只能出生在实际E/F区域地板。
        if region not in {"E", "F"} or position not in indexed[region].floors:
            # 不用画面位置冒充合法路径。
            raise ValueError("鸡出生点无效")
        # 冻结节点值。
        spawns.append((region, *position))
    # 至少一只鸡且巢与出生点一一对应。
    if not spawns or len(spawns) != kinds.count("nest"):
        # 不让缺巢索引在模拟阶段才异常。
        raise ValueError("鸡出生点与巢数量不一致")
    # 全部引用通过后提交完整静态地图。
    return LevelDefinition(rooms, initial_region, initial_position, tuple(spawns))

# 直接接收模型定义的公开构造也必须经过与JSON相同的实际边界。
def validate_definitions(level: LevelDefinition, rules: RulesDefinition) -> tuple[LevelDefinition, RulesDefinition]:
    # 类型必须为本契约的数据类，不用任意对象伪装相同属性。
    if type(level) is not LevelDefinition or type(rules) is not RulesDefinition:
        # 错误不会留到帧循环才表现为属性异常。
        raise ValueError("会话定义类型非法")
    # 根定义必须使用不可变元组。
    if type(level.rooms) is not tuple or type(level.chicken_spawns) is not tuple or type(rules.melodies) is not tuple:
        # 冻结外壳不保证嵌套列表安全，必须实际核验。
        raise ValueError("地图与曲谱嵌套定义必须不可变")
    # 曲谱数据可转换为同一纯校验契约，但不能接受原始可变音符。
    melody_values = []
    # 核验每个数据类及其嵌套事件。
    for melody in rules.melodies:
        # 类型与音符容器必须与正式定义一致。
        if type(melody) is not MelodyDefinition or type(melody.notes) is not tuple:
            # 不让输入列表被另一个线程或界面改写。
            raise ValueError("曲谱定义必须冻结")
        # 音符类型、数量、音区与实际演奏共源。
        validate_notes(melody.notes, require_integer(rules.max_notes, 1, 64))
        # 转为校验输入不会保留外部可变容器。
        melody_values.append({"id": melody.id, "name": melody.name, "notes": [list(note) for note in melody.notes],
                              # 效果与分类由parse_rules核验。
                              "effect": melody.effect, "category": melody.category})
    # 行为数值都再次经过实际边界，不因有类型标注就放行。
    checked_rules = parse_rules({"schema_version": 1, "melodies": melody_values,
                                 # 单位和警告窗口继续使用同一正式校验。
                                 "movement_seconds": rules.movement_seconds, "warning_seconds": rules.warning_seconds,
                                 # 鸡追逐及返巢都必须有限。
                                 "chicken_step_seconds": rules.chicken_step_seconds,
                                 # 参数不做默认覆盖合法零或非法值。
                                 "return_step_seconds": rules.return_step_seconds, "exit_seconds": rules.exit_seconds,
                                 # 最大前缀与动画时长都真实核验。
                                 "max_notes": rules.max_notes, "box_seconds": rules.box_seconds,
                                 # 长坡仍只作为有限A至B过场。
                                 "slide_seconds": rules.slide_seconds})
    # 各区域还原为与JSON装载相同的准确结构。
    room_values = []
    # 每个房间都是冻结数据，所有内层同样核验。
    for room in level.rooms:
        # 必要不可变容器必须是真实对应类型。
        if type(room) is not RoomDefinition or type(room.floors) is not frozenset or type(room.territory) is not frozenset or any(type(value) is not tuple for value in (room.portals, room.objects, room.landmarks, room.pedestal_steps)):
            # 防止外层dataclass冻结掩盖内层可变集合。
            raise ValueError("区域嵌套定义必须冻结")
        # 在生成行之前检查网格大小，避免任意巨大循环。
        width = require_integer(room.width, 3, 128)
        # 高度同样先严格检查。
        height = require_integer(room.height, 3, 128)
        # 地板和领地每点须实际不可变及在房间以内。
        for position in room.floors | room.territory:
            # 元组型格坐标才允许共享。
            if type(position) is not tuple or len(position) != 2:
                # 不从错误成员猜坐标。
                raise ValueError("区域格坐标必须不可变")
            # 类型、非负与最大格数校验一致。
            require_position(list(position))
            # 不把墙外地板在转成rows时丢弃。
            if position[0] >= width or position[1] >= height:
                # 原始越界必须失败。
                raise ValueError("区域格坐标越界")
        # 门定义及坐标必须真实冻结。
        portals = []
        # 转换不会改变原始门数据。
        for portal in room.portals:
            # 元组位置与真实门类型缺一不可。
            if type(portal) is not PortalDefinition or type(portal.position) is not tuple or type(portal.target_position) is not tuple:
                # 不接受冻结外壳里可变位置。
                raise ValueError("门定义必须冻结")
            # 位置形状在建立列表前校验。
            require_position(list(portal.position))
            # 目标位置同样严格核验。
            require_position(list(portal.target_position))
            # 之后parse_room与parse_level核验真实落脚与条件。
            portals.append({"id": portal.id, "position": list(portal.position), "direction": portal.direction,
                            # 目标引用不通过字符串转换掩盖非法类型。
                            "target_region": portal.target_region, "target_position": list(portal.target_position),
                            # 种类和提示分别保留。
                            "condition": portal.condition, "label": portal.label, "kind": portal.kind})
        # 物件坐标也不应泄露外部可变数据。
        objects = []
        # 所有交互物复用正式内容引用边界。
        for item in room.objects:
            # 检查真实物件类型和原始坐标容器。
            if type(item) is not InteractiveObject or type(item.position) is not tuple or item.target_position is not None and type(item.target_position) is not tuple:
                # 不接受外部任意对象充当交互物。
                raise ValueError("物件定义必须冻结")
            # 当前物件实际格坐标核验。
            require_position(list(item.position))
            # 定义的必要字段不会被强制字符串化。
            value = {"id": item.id, "kind": item.kind, "position": list(item.position), "payload": item.payload}
            # 只有显式货箱目标才带入位置校验。
            if item.target_position is not None:
                # 目标在当前区域的地板约束继续由parse_room检查。
                value["target_position"] = list(item.target_position)
            # 追加本次独立校验值。
            objects.append(value)
        # 地标和石座矩形内层必须真实不可变。
        if any(type(value) is not tuple for value in (*room.landmarks, *room.pedestal_steps)):
            # 不放行混入的列表或可变对象。
            raise ValueError("地标及石座定义必须冻结")
        # 地形转成字串与JSON解析逻辑保持一致。
        rows = ["".join("." if (x, y) in room.floors else "#" for x in range(width))
                # 每一行具有明确相同宽度。
                for y in range(height)]
        # 房间基础值仍将由parse_room进行范围与引用检查。
        room_values.append({"id": room.id, "name": room.name, "width": width, "height": height,
                            # 动态物与静态字符分离。
                            "rows": rows, "portals": portals, "objects": objects,
                            # 地标、领地与平台全部检查后重新冻结。
                            "territory": [list(position) for position in room.territory],
                            # 地标格式仍由专属边界核验。
                            "landmarks": [list(value) for value in room.landmarks],
                            # 层矩形不允许侵入地板。
                            "pedestal_steps": [list(value) for value in room.pedestal_steps]})
    # 初始坐标与出生点也必须为不可变值。
    if type(level.initial_position) is not tuple or any(type(spawn) is not tuple for spawn in level.chicken_spawns):
        # 数据类外壳不代替内层验证。
        raise ValueError("初始落脚及鸡出生点必须冻结")
    # 通过同一跨区边界重新建立独立冻结配置。
    checked_level = parse_level({"schema_version": 1, "initial_region": level.initial_region,
                                 # 正式初始格与配置保持同一来源。
                                 "initial_position": list(level.initial_position),
                                 # 出生点一一对应真实巢，不能丢弃或默认替换。
                                 "chicken_spawns": [list(spawn) for spawn in level.chicken_spawns],
                                 # 全部房间已转换为准确本版结构。
                                 "rooms": room_values}, checked_rules)
    # 会话只持有这一份实际校验后的不可变配置。
    return checked_level, checked_rules
