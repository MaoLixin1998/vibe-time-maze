# JSON读取仅发生在显式加载接口，模型不依赖该适配器。
import json
# 包资源定位不依赖当前工作目录或开发机绝对路径。
from importlib.resources import files
# 游戏文字导出只读映射，防止多个界面相互改写。
from types import MappingProxyType
# 返回契约使用标准只读映射类型。
from collections.abc import Mapping
# 配置冻结与边界检查交给纯模型解析函数。
from time_maze.model.level_validation import parse_level, parse_rules, require_id, require_integer
# 地图类型便于公开接口标注。
from time_maze.model.level_definition import LevelDefinition
# 规则与窗口设备无关。
from time_maze.model.rules_definition import RulesDefinition
# 七区按清单组合，主体不会读取本机归档。
from time_maze.adapters.area_loader import assemble_level

# JSON同一对象重复键时直接拒绝，不以最后一项覆盖。
def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    # 每个JSON对象有独立解析容器。
    value = {}
    # 保留键顺序并逐项核验。
    for key, item in pairs:
        # 配置重复字段属于数据错误。
        if key in value:
            # 带出原字段名，不吞掉原因。
            raise ValueError(f"JSON重复字段: {key}")
        # 无歧义时才记录该值。
        value[key] = item
    # 临时字典随后由纯模型冻结。
    return value

# JSON非标准NaN与Infinity常量拒绝进入数据边界。
def _reject_constant(value: str) -> None:
    # 原始常量不是合法正式资源。
    raise ValueError(f"JSON非有限常量: {value}")

# 严格解析正式JSON文本，工具可用同一边界检查索引blob而不执行索引源码。
def decode_json(content: str) -> object:
    # 大型误放资源在解析前拒绝，避免巨量分配。
    if len(content) > 1_000_000:
        # 正式七区基础数据远小于该上限。
        raise ValueError("运行资源过大")
    # 同时拒绝重复字段和非标准数字。
    return json.loads(content, object_pairs_hook=_unique_object, parse_constant=_reject_constant)

# 从包内准确资源读取一次，不搜索制作素材。
def _read_json(name: str) -> object:
    # 文件名只由加载器稳定常量和严格校验后的区域清单提供。
    resource = files("time_maze").joinpath("data", name)
    # UTF-8严格读取，编码错误保留为加载失败。
    content = resource.read_text(encoding="utf-8")
    # 包装载与只读检查共用拒绝重复字段和非法数字的边界。
    return decode_json(content)

# 显式加载正式数据，成功后仅返回冻结模型和只读文字。
def load_content() -> tuple[LevelDefinition, RulesDefinition, Mapping[str, str]]:
    # 先冻结曲谱及参数，地图谱箱引用使用这些正式ID核验。
    rules = parse_rules(_read_json("rules.json"))
    # 静态地形和全部跨区落脚一起校验。
    level = parse_level(assemble_level(_read_json("level.json"), _read_json), rules)
    # 游戏文字独立读取，不通过文字反推规则。
    text = _read_json("text.json")
    # 根格式及版本是必要边界，不接受列表或缺版本。
    if type(text) is not dict or "schema_version" not in text:
        # 不回退成空文字导致无法玩。
        raise ValueError("游戏文字格式无效")
    # 同一版文字资源与正式加载契约一致。
    require_integer(text["schema_version"], 1, 1)
    # 去掉格式元信息，只返回实际显示文字。
    values = {}
    # 每个键都作为稳定文字ID核验。
    for key, value in text.items():
        # 版本元信息已经核验，不当显示文案导出。
        if key == "schema_version":
            # 保持返回映射值全部为字符串。
            continue
        # 禁止不明确的文字ID。
        require_id(key)
        # 空控制提示不视为有效文字。
        if type(value) is not str or not value or len(value) > 512:
            # 不通过str转换掩盖非法类型。
            raise ValueError(f"游戏文字无效: {key}")
        # 复制进入本次加载自己的字典。
        values[key] = value
    # 必要提示必须存在，不只在开发机中文界面依赖默认值。
    if not {"title", "controls"} <= values.keys():
        # 错误在启动边界清晰显示。
        raise ValueError("缺少游戏标题或操作提示")
    # MappingProxyType阻止下游写入显示来源。
    return level, rules, MappingProxyType(values)
