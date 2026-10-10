# 快照采用冻结数据类，不向渲染泄露模型可变容器。
from dataclasses import dataclass
# 事件同样为不可变值，消费不会改动业务。
from time_maze.model.game_event import GameEvent

# 每次查询创建完整只读展示值，嵌套数据只使用元组。
# 冻结数据类禁止字段重赋值，嵌套容器另按模型边界核验。
@dataclass(frozen=True)
class GameSnapshot:
    # 玩家当前区域ID。
    region: str
    # 碰撞使用已经提交的格坐标。
    pos: tuple[int, int]
    # 插值展示坐标不参与碰撞。
    visual_pos: tuple[float, float]
    # child或adult表示年龄能力。
    age: str
    # 年份来自年龄映射，不读取电脑日期。
    year: int
    # 唯一全局昼夜状态。
    is_day: bool
    # 当前玩家流程阶段。
    phase: str
    # 暂停冻结模拟，不禁止刷新展示。
    is_paused: bool
    # 真正跨过F出口后记胜利。
    is_won: bool
    # 奖励领取独立于迷宫胜利。
    reward_claimed: bool
    # 共享货运通道是否已推开。
    box_open: bool
    # 货箱推移动画归一化进度。
    box_progress: float
    # 两张随身谱的稳定ID。
    collected_scores: tuple[str, ...]
    # 已开启谱箱的稳定ID。
    opened_chests: tuple[str, ...]
    # 当前时代鸡的只读位置与行为。
    chickens: tuple[tuple[str, int, int, str], ...]
    # 两个时代鸡的完整不可变业务恢复数据。
    chicken_state: tuple
    # 有界结果事件历史供消费者按序号去重。
    events: tuple[GameEvent, ...]
    # 最近真实操作反馈。
    message: str
    # 邻近提示与真实门条件共用规则。
    nearby_hint: str
    # 滑落、推箱或出口过场归一化进度。
    cutscene_progress: float
    # 货箱所在区域和展示位置从正式路径定义生成。
    box_region: str
    # 插值只表达向北推到凹位，不改变碰撞终点。
    box_visual_pos: tuple[float, float]
    # 夜门当前占用格供渲染与完整业务恢复共用。
    held_thresholds: tuple[tuple[str, tuple[int, int]], ...]
