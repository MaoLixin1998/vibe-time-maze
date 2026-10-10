# 静态房间用冻结数据类供模型与渲染共享。
from dataclasses import dataclass
# 门槛是静态定义，房间只持有不可变元组。
from time_maze.model.portal_definition import PortalDefinition
# 交互物同样不承载运行时可变状态。
from time_maze.model.interactive_object import InteractiveObject

# 每区只有一份静态地形，年龄和昼夜不复制整张地图。
# 冻结数据类禁止字段重赋值，嵌套容器另按模型边界核验。
@dataclass(frozen=True)
class RoomDefinition:
    # 稳定区域ID为A至G。
    id: str
    # 名称仅用于玩家展示。
    name: str
    # 网格宽度以格为单位。
    width: int
    # 网格高度以格为单位。
    height: int
    # 合法地板格用frozenset防止运行对象改写地图。
    floors: frozenset[tuple[int, int]]
    # 出入口使用静态门槛定义。
    portals: tuple[PortalDefinition, ...]
    # 地图上的独立交互物定义。
    objects: tuple[InteractiveObject, ...]
    # 鸡领地标记只影响警戒，不改变玩家地板。
    territory: frozenset[tuple[int, int]]
    # 固定地标含坐标和显示文字，不作为通关flag。
    landmarks: tuple[tuple[int, int, str], ...]
    # 石台各层矩形只供静态几何表达，外围层与非通行地板同源。
    pedestal_steps: tuple[tuple[int, int, int, int], ...] = ()
