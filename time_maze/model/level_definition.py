# 冻结数据类保护七区静态配置。
from dataclasses import dataclass
# 区域类型单独成文件，避免一份源码混合多个类。
from time_maze.model.room_definition import RoomDefinition

# 地图只负责已校验的静态定义和按ID查询。
# 冻结数据类禁止字段重赋值，嵌套容器另按模型边界核验。
@dataclass(frozen=True)
class LevelDefinition:
    # 房间元组及其嵌套定义全部不可变。
    rooms: tuple[RoomDefinition, ...]
    # 初始区域是正常玩家入口。
    initial_region: str
    # 初始格位于剑台旁合法安全地面。
    initial_position: tuple[int, int]
    # 鸡的初始位置与巢顺序对应，便于不同地图使用同一行为模型。
    chicken_spawns: tuple[tuple[str, int, int], ...] = ()

    # 按稳定ID查询区域，未知ID保留明确异常原因。
    def room(self, region_id: str) -> RoomDefinition:
        # 仅七区的小型元组无需额外可变索引。
        for room in self.rooms:
            # 返回与请求ID对应的唯一已校验定义。
            if room.id == region_id:
                # 不复制或暴露可变地图数据。
                return room
        # 未知区域属于调用边界错误。
        raise ValueError(f"未知区域: {region_id}")
