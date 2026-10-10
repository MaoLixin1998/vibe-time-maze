# 数值边界与其他模型入口复用同一实际有限性及溢出校验。
from time_maze.model.level_validation import require_finite_number
# 位置和方向边界与其他纯移动能力共用。
from time_maze.model.movement import validate_position, DIRECTION_STEPS

# 玩家只保存位置、朝向和移动插值，不决定门或时代。
class Player:
    # 初始参数由已校验地图提供；移动时间以秒计。
    def __init__(self, region: str, position: tuple[int, int], movement_seconds: float):
        # 初始区域必须是明确非空ID。
        if type(region) is not str or not region:
            # 不把任意对象转为区域名称。
            raise ValueError("玩家区域必须为非空字符串")
        # 合法不可变坐标才进入实例状态。
        validate_position(position)
        # 类型、有限性和浮点表示溢出先统一检查。
        duration = require_finite_number(movement_seconds)
        # 插值时长还必须为正秒数。
        if duration <= 0.0:
            # 不让零时长造成除零或无穷移动。
            raise ValueError("每格移动时长必须为有限正秒")
        # 当前区域属于本实例。
        self._region = region
        # 格坐标在移动开始时原子提交。
        self._position = position
        # 朝向供需要特定站位的交互查询。
        self._direction = "down"
        # 保存每格插值总时长。
        self._movement_seconds = duration
        # 原始展示坐标始终与自己的状态关联。
        self._visual_start = (float(position[0]), float(position[1]))
        # 零值表示当前没有未完成插值。
        self._remaining_seconds = 0.0

    # 当前区域是只读查询，不返回可变引用。
    @property
    def region(self) -> str:
        # 直接返回稳定区域值。
        return self._region

    # 逻辑位置是不可变格坐标。
    @property
    def position(self) -> tuple[int, int]:
        # 返回已提交碰撞坐标。
        return self._position

    # 当前朝向供推物验证。
    @property
    def direction(self) -> str:
        # 返回最近合法方向输入。
        return self._direction

    # 是否在插值期间用于禁止重复提交移动。
    @property
    def is_moving(self) -> bool:
        # 插值完成后才允许下一步。
        return self._remaining_seconds > 0.0

    # 展示坐标不会改变碰撞及触发结果。
    @property
    def visual_position(self) -> tuple[float, float]:
        # 从剩余秒数计算零到一之间的进度。
        progress = 1.0 - self._remaining_seconds / self._movement_seconds
        # 对每个坐标进行线性插值。
        return tuple(start + (end - start) * progress
                     # 目标为已提交格，源为上次完整格。
                     for start, end in zip(self._visual_start, self._position))

    # 输入被墙挡住时仍允许转身，方便推箱交互。
    def face(self, direction: str) -> None:
        # 即使独立调用也要保持正式方向契约。
        if type(direction) is not str or direction not in DIRECTION_STEPS:
            # 错方向不写入状态。
            raise ValueError("玩家方向非法")
        # 方向由会话边界预先校验。
        self._direction = direction

    # 原子提交一次同区合法移动并开始展示插值。
    def move_to(self, position: tuple[int, int]) -> None:
        # 不允许外部列表或非法格进入玩家位置。
        validate_position(position)
        # 插值未完成不能覆盖源位置造成跳步。
        if self.is_moving:
            # 公开调用保留明确忙碌原因。
            raise ValueError("玩家仍在移动")
        # 记录当前完整格为插值起点。
        self._visual_start = (float(self._position[0]), float(self._position[1]))
        # 更新碰撞位置，避免插值穿过障碍才判定。
        self._position = position
        # 每格采用规则中同一时长。
        self._remaining_seconds = self._movement_seconds

    # 跨区与恢复直接落在已经验证的完整格。
    def place(self, region: str, position: tuple[int, int]) -> None:
        # 跨区和恢复必须提供明确区域。
        if type(region) is not str or not region:
            # 类型错误不改变当前玩家状态。
            raise ValueError("玩家区域必须为非空字符串")
        # 两字段校验通过后再成组提交。
        validate_position(position)
        # 同时提交区域和合法落脚点。
        self._region = region
        # 位置不保留另一房间的旧值。
        self._position = position
        # 取消跨区前插值，避免跨图画出长线。
        self._visual_start = (float(position[0]), float(position[1]))
        # 完整格允许下一次移动或演奏。
        self._remaining_seconds = 0.0

    # 受控正时间步只推进画面插值。
    def update(self, seconds: float) -> None:
        # 独立组件也将超出浮点表示范围的整数转换为明确ValueError。
        elapsed_seconds = require_finite_number(seconds)
        # 不允许负时间将移动插值倒退。
        if elapsed_seconds < 0.0:
            # 不用零值回退吞掉调用错误。
            raise ValueError("玩家时间步必须为有限非负秒")
        # 不允许剩余秒数降为负数。
        self._remaining_seconds = max(0.0, self._remaining_seconds - elapsed_seconds)
