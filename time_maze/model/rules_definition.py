# 行为参数冻结后作为每局独立状态的只读输入。
from dataclasses import dataclass
# 曲谱数据不向模型引入文件或声音依赖。
from time_maze.model.melody_definition import MelodyDefinition

# 规则只描述输入匹配、移动时间和追逐参数。
# 冻结数据类禁止字段重赋值，嵌套容器另按模型边界核验。
@dataclass(frozen=True)
class RulesDefinition:
    # 曲谱完整顺序和匹配行为由单一来源控制。
    melodies: tuple[MelodyDefinition, ...]
    # 每格移动时间以秒为单位。
    movement_seconds: float
    # 白天鸡追逐前必须提供完整警告窗口。
    warning_seconds: float
    # 鸡追逐每一步的间隔，单位为秒。
    chicken_step_seconds: float
    # 鸡归巢每一步的间隔，单位为秒。
    return_step_seconds: float
    # 出口展示是可跳过的有限过场，单位为秒。
    exit_seconds: float
    # 输入面板最大音符数避免无限前缀。
    max_notes: int
    # 成年推动重物是有限正式过场，单位为秒。
    box_seconds: float = 1.2
    # 滑落只连接A与B，不生成额外区域。
    slide_seconds: float = 0.9
