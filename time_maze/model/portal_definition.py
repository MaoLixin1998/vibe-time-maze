# 用不可变数据类保存静态门槛及其真实通行条件。
from dataclasses import dataclass

# 门槛只描述静态连接，开闭结果由当前游戏状态查询。
# 冻结数据类禁止字段重赋值，嵌套容器另按模型边界核验。
@dataclass(frozen=True)
class PortalDefinition:
    # 每个门槛具有独立稳定ID，文字变化不改变规则。
    id: str
    # 玩家先走到该格，再沿出口方向跨区。
    position: tuple[int, int]
    # 合法方向采用up、down、left、right。
    direction: str
    # 目标区域ID由地图边界校验。
    target_region: str
    # 跨区后的落脚格必须属于目标地板。
    target_position: tuple[int, int]
    # 条件ID与邻近提示共用，避免提示和碰撞不一致。
    condition: str
    # 简短用途文字不揭示未知排水口的正确答案。
    label: str
    # 滑落与普通门使用相同拓扑，过场行为由种类区分。
    kind: str = "door"
