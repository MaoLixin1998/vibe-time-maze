# 归一化进度与其他秒数入口共用有限数及浮点溢出边界。
from time_maze.model.level_validation import require_finite_number
# 门占用坐标与玩家位置使用同一纯边界。
from time_maze.model.movement import validate_position

# 货运箱及门槛保留状态与地图静态定义分离。
class MazeState:
    # 每次游戏只创建一份跨龄共享货箱状态。
    def __init__(self):
        # 初始货运门被唯一重物挡住。
        self._box_open = False
        # 动画零值表示尚未推开。
        self._box_progress = 0.0
        # 被占用时延迟关闭的夜闸以门槛坐标标记。
        self._held_thresholds = set()

    # 通道开通状态不会随年龄或昼夜重置。
    @property
    def box_open(self) -> bool:
        # 返回已完成的真实开通状态。
        return self._box_open

    # 推物归一化进度供展示查询。
    @property
    def box_progress(self) -> float:
        # 查询不推进动画。
        return self._box_progress

    # 推物阶段由会话验证成年及站位后更新。
    def set_box_progress(self, progress: float) -> None:
        # 先统一拒绝bool、NaN、无穷与巨量整数表示溢出。
        checked_progress = require_finite_number(progress)
        # 公开进度不吞掉超出动画区间的合法有限数字。
        if not 0.0 <= checked_progress <= 1.0:
            # 会话负责将合法有限动画比值限定，组件拒绝非法调用。
            raise ValueError("货箱进度必须为零至一有限数值")
        # 已校验动画进度整体提交。
        self._box_progress = checked_progress
        # 只有完整到达指定终点才开放货路。
        self._box_open = self._box_progress >= 1.0

    # 夜间改白天时标记正在占用的门槛。
    def hold_threshold(self, region: str, position: tuple[int, int]) -> None:
        # 门占用不接受任意外部区域类型。
        if type(region) is not str or not region:
            # 校验失败不建立虚假占用。
            raise ValueError("门槛区域必须为非空字符串")
        # 坐标必须为真正不可变格。
        validate_position(position)
        # 状态属于本局，既不修改地图也不转移玩家。
        self._held_thresholds.add((region, position))

    # 玩家离开门槛后清除不再占用的延迟关闭状态。
    def release_unused(self, region: str, position: tuple[int, int]) -> None:
        # 当前实际格需要合法不可变坐标。
        validate_position(position)
        # 区域类型错误不能把所有合法门占用清空。
        if type(region) is not str or not region:
            # 不改状态后再报错。
            raise ValueError("门槛区域必须为非空字符串")
        # 只保留实际站立处，离开后下次不能重新借旧门通行。
        self._held_thresholds.intersection_update({(region, position)})

    # 门条件查询只读取精确占用状态。
    def is_threshold_held(self, region: str, position: tuple[int, int]) -> bool:
        # 判断指定门槛是否因占用暂时放行。
        return (region, position) in self._held_thresholds

    # 恢复货箱与占用门槛的不可变快照。
    def restore(self, box_open: bool, box_progress: float, thresholds: tuple) -> None:
        # 无副作用校验阶段先检查数值可表示性及有限性。
        progress = require_finite_number(box_progress)
        # 开通布尔和进度必须表达同一真实终点。
        if type(box_open) is not bool or not 0.0 <= progress <= 1.0 or box_open != (progress == 1.0):
            # 无效恢复数据不能造成半开通状态。
            raise ValueError("货箱恢复状态不一致")
        # 门占用是不可变业务恢复值。
        if type(thresholds) is not tuple or any(type(item) is not tuple or len(item) != 2 or type(item[0]) is not str or type(item[1]) is not tuple or len(item[1]) != 2 or any(type(value) is not int or value < 0 for value in item[1]) for item in thresholds):
            # 不接收可变嵌套结构。
            raise ValueError("门槛恢复状态非法")
        # 开通状态与动画进度一起恢复。
        self._box_open = box_open
        # 进度来自完整检查点，不继承失败前动画。
        self._box_progress = progress
        # 创建自己的集合，防止多个实例共享引用。
        self._held_thresholds = set(thresholds)

    # 为完整检查点导出不可变占用数据。
    def threshold_snapshot(self) -> tuple:
        # 排序保证测试及重试可复现。
        return tuple(sorted(self._held_thresholds))
