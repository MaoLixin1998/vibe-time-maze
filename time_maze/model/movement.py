# 广度优先队列属于纯内存计算，不引入IO。
from collections import deque
# 只读映射保护稳定方向表，不能被其他模块改写。
from types import MappingProxyType
# 地图定义只作为不可变计算输入。
from time_maze.model.level_definition import LevelDefinition

# 四方向坐标增量以格为单位，y向下增长。
DIRECTION_STEPS = MappingProxyType({"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)})

# 格坐标必须为不可变二项非负整数值。
def validate_position(position: tuple[int, int]) -> tuple[int, int]:
    # bool不能冒充格坐标，最高127对应本格式128格上限且避免巨大整数转浮点溢出。
    if type(position) is not tuple or len(position) != 2 or any(type(value) is not int or not 0 <= value <= 127 for value in position):
        # 不做取整、补零或静默夹紧。
        raise ValueError("格坐标必须为二项非负整数元组")
    # 已合法值无需复制。
    return position

# 计算下一个格；非法方向在公开输入处拒绝。
def adjacent(position: tuple[int, int], direction: str) -> tuple[int, int]:
    # 坐标经过模型边界校验后再计算。
    validate_position(position)
    # 非法方向不能泄露含糊KeyError。
    if type(direction) is not str or direction not in DIRECTION_STEPS:
        # 调用错误保持清楚输入契约。
        raise ValueError("相邻格方向非法")
    # 固定增量不随玩家或地图变化。
    step = DIRECTION_STEPS[direction]
    # 返回独立坐标值。
    return position[0] + step[0], position[1] + step[1]

# 小地图曼哈顿距离供邻近物件交互使用。
def distance(first: tuple[int, int], second: tuple[int, int]) -> int:
    # 相邻正交格距离为一，不把隔角当邻近。
    return abs(first[0] - second[0]) + abs(first[1] - second[1])

# 在地板上计算确定性最短路径，鸡只使用E与F正确排水口。
def chicken_path(level: LevelDefinition, start: tuple, goal: tuple) -> tuple:
    # 空起点即终点不需要移动。
    if start == goal:
        # 返回完整路径，调用者不会弹出不存在的下一步。
        return (start,)
    # 队列保存待扩展节点，避免递归受地图大小影响。
    pending = deque([start])
    # 每个节点只记录第一次到达的父节点。
    parents = {start: None}
    # 广度优先保证单位格路径最短。
    while pending:
        # 按固定顺序扩展，结果可复现。
        current = pending.popleft()
        # 节点由区域和格坐标组成。
        region, x, y = current
        # 当前区域地板不会被行为改写。
        room = level.room(region)
        # 先加入本区域正交邻格。
        neighbors = [(region, *adjacent((x, y), direction))
                     # 四方向顺序固定，避免随机鸡线路。
                     for direction in DIRECTION_STEPS
                     # 鸡不穿过静态墙。
                     if adjacent((x, y), direction) in room.floors]
        # 跨区只使用E与F之间的正确排水口。
        for portal in room.portals:
            # 到门槛才允许加入目标落脚，不能直接跳到巢里。
            if portal.position == (x, y) and {region, portal.target_region} == {"E", "F"}:
                # 不按玩家年龄过滤鸡的固定归巢通道。
                neighbors.append((portal.target_region, *portal.target_position))
        # 检查各个真实可达邻格。
        for neighbor in neighbors:
            # 每个节点只入队一次。
            if neighbor in parents:
                # 已探索节点不用重复寻路。
                continue
            # 保存路径前驱。
            parents[neighbor] = current
            # 已到目标就重建完整不可变路径。
            if neighbor == goal:
                # 从目标向起点还原。
                path = [goal]
                # 循环直到最早起点没有父节点。
                while parents[path[-1]] is not None:
                    # 添加上一个真实节点。
                    path.append(parents[path[-1]])
                # 正向路径供一步移动使用。
                return tuple(reversed(path))
            # 其他节点等待之后扩展。
            pending.append(neighbor)
    # 无法到达时保留原地，不瞬移或穿墙。
    return (start,)
