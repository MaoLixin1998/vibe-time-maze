# 出口规则只依赖公开门定义，不依赖会话内部字段。
from time_maze.model.portal_definition import PortalDefinition

# 真正跨过孩童白天出口才结束迷宫追逐并开始G展开。
def is_meadow_exit(portal: PortalDefinition) -> bool:
    # 实际通行已由共享条件校验，此处标识唯一胜利入口。
    return portal.condition == "child_day" and portal.target_region == "G"
