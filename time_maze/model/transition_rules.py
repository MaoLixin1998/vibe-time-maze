# 门槛条件只读取正式定义与已封装的会话状态。
from time_maze.model.portal_definition import PortalDefinition

# 同一条件同时返回通行结果与玩家可读原因。
def portal_access(portal: PortalDefinition, age: str, is_day: bool,
                  box_open: bool, is_held: bool = False) -> tuple[bool, str]:
    # 普通路无需时代或相位条件。
    if portal.condition == "open":
        # 普通门只展示其用途名称。
        return True, portal.label
    # 窄门及排水口用同一年龄能力规则。
    if portal.condition == "child":
        # 成年不能被允许挤进孩童通道。
        return age == "child", portal.label + " · 仅孩童可通行"
    # 货路开通后适用于两龄和昼夜。
    if portal.condition == "cargo":
        # 不能因为成年就穿过尚未推开的重物。
        return box_open, portal.label + (" · 已开通" if box_open else " · 重物挡路，成年可从货廊推开")
    # 夜间门允许当前占用者在切白天后安全离开。
    if portal.condition == "night":
        # 白天占用者可以离开，提示不误报成完全关闭。
        if is_day and is_held:
            # 不改变玩家坐标，离开才关门。
            return True, portal.label + " · 占用中，离开后关闭"
        # 不移动或弹出门槛上的玩家。
        return not is_day or is_held, portal.label + (" · 夜间开放" if not is_day else " · 白天关闭")
    # 真正出口同时需要孩童和白天。
    if portal.condition == "child_day":
        # 提示与胜利跨门校验同源。
        return age == "child" and is_day, portal.label + " · 仅孩童白天可通行"
    # 未知条件属于配置错误，不能悄悄当普通门。
    raise ValueError(f"未知门条件: {portal.condition}")
