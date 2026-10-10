# 独立路径规划只使用公开地图和快照，不读取模型私有字段。
from collections import deque
# 正式模型创建不需要窗口或音频设备。
from time_maze.model.game_session import GameSession
# 正式数据从安装包内加载。
from time_maze.adapters.content_loader import load_content

# 回归方向增量用于独立网格BFS，不调用被测移动函数生成预期。
STEPS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

# 从默认入口创建真实正式会话。
def new_session() -> GameSession:
    # 从包资源得到不可变关卡和规则。
    level, rules, _ = load_content()
    # 组件状态由新会话独立创建。
    return GameSession(level, rules)

# 按公开更新时间推进确定性时长，遵守会话追赶上限。
def advance(session: GameSession, seconds: float) -> None:
    # 以0.05秒步长推进，避免一次大dt被限幅而伪造验证。
    remaining = seconds
    # 推进到实际要求的全部时间。
    while remaining > 0.000001:
        # 最后一步不能超出指定时长。
        step = min(0.05, remaining)
        # 世界由真实模型更新，不通过测试直改状态。
        session.update(step)
        # 递减余量，保证有限循环。
        remaining -= step

# 在当前区域用独立BFS规划合法地板，动态箱子视为真实障碍。
def walk_to(session: GameSession, target: tuple[int, int]) -> None:
    # 当前房间只读取公开定义。
    snapshot = session.snapshot()
    # 地板静态集合不会被测试反写。
    room = session.level.room(snapshot.region)
    # 队列记录待探索坐标。
    pending = deque([snapshot.pos])
    # 每个格只保留第一个前驱与方向。
    parents = {snapshot.pos: None}
    # 当前箱子由公开快照计算碰撞格。
    blocked = {tuple(round(value) for value in snapshot.box_visual_pos)} if snapshot.box_region == room.id else set()
    # 目标在同一房间寻找完整路径。
    while pending and target not in parents:
        # 拿出最早待探索的格子。
        current = pending.popleft()
        # 按确定性方向枚举邻格。
        for direction, step in STEPS.items():
            # 相邻位置不使用被测movement模块。
            neighbor = (current[0] + step[0], current[1] + step[1])
            # 地板、箱子和已访问状态明确筛选。
            if neighbor not in room.floors or neighbor in blocked or neighbor in parents:
                # 无效节点不入队。
                continue
            # 保存方向供后续真实输入使用。
            parents[neighbor] = (current, direction)
            # 下一轮继续探索。
            pending.append(neighbor)
    # 目标不可达是测试失败，不瞬移玩家绕过问题。
    if target not in parents:
        # 保留区域和坐标便于检查布局。
        raise AssertionError(f"No public route: {room.id} {snapshot.pos} -> {target}")
    # 从目标还原真实方向序列。
    directions = []
    # 当前还原节点从目标开始。
    current = target
    # 起点的前驱为空。
    while parents[current] is not None:
        # 解包前驱和方向。
        previous, direction = parents[current]
        # 记录正向动作，末尾统一反转。
        directions.append(direction)
        # 沿前驱回到起点。
        current = previous
    # 逐步调用公开移动能力。
    for direction in reversed(directions):
        # 移动失败保留真实结果，不直接改位置。
        if not session.move(direction):
            # 门关闭、被抓或碰撞错误都应暴露。
            raise AssertionError(f"Move rejected: {session.snapshot()}")
        # 等待该格的真实移动插值结束。
        advance(session, session.rules.movement_seconds + 0.01)

# 到达门槛后跨越同一真实边界，不能把演奏当胜利。
def cross(session: GameSession, portal_id: str) -> None:
    # 按稳定门ID找当前区域的正式定义。
    portal = next(item for item in session.level.room(session.snapshot().region).portals if item.id == portal_id)
    # 玩家先自行移动至合法门槛。
    walk_to(session, portal.position)
    # 向出口方向下一步才请求跨区。
    if not session.move(portal.direction):
        # 条件不满足时不伪造跨门。
        raise AssertionError(f"Portal rejected: {portal_id}")
    # 普通移动完成后才能继续输入。
    advance(session, session.rules.movement_seconds + 0.01)
    # 滑落动画必须通过真实更新完成。
    if session.snapshot().phase == "sliding":
        # 滑落时长取正式规则，禁止测试拍摄跳转。
        advance(session, session.rules.slide_seconds + 0.01)

# 走到对象邻近格再交互，避免直接领取远处宝箱。
def interact_with(session: GameSession, object_id: str) -> str:
    # 当前房间对象只读查询。
    room = session.level.room(session.snapshot().region)
    # 稳定对象ID是目标，不依赖显示文字。
    target = next(item for item in room.objects if item.id == object_id)
    # 箱子必须从南侧向北施力，其他对象优先下方。
    position = (target.position[0], target.position[1] + 1)
    # 有地板时采用明确邻近站位。
    if position not in room.floors:
        # 找可站的正交邻格，保持真实碰撞约束。
        position = next((target.position[0] + dx, target.position[1] + dy) for dx, dy in STEPS.values()
                        # 不进入墙内施力或领取。
                        if (target.position[0] + dx, target.position[1] + dy) in room.floors)
    # 路线沿公开地板走完整，不瞬移。
    walk_to(session, position)
    # 货箱要求真实向北施力；朝箱迈步被碰撞拒绝，但公开操作会更新朝向。
    if target.kind == "cargo_box":
        # 不绕过碰撞，只让玩家面向正北箱子后再交互。
        session.move("up")
    # 世界效果由正式邻近交互提交。
    return session.interact()

# 根据正式匹配定义演奏，不直改昼夜或隐藏彩蛋状态。
def play(session: GameSession, melody_id: str) -> str:
    # 使用同源曲谱，包含真实长度和八度。
    melody = next(item for item in session.rules.melodies if item.id == melody_id)
    # 提交的是音符事件，不调用Timeline私有状态。
    return session.play_keyboard(melody.notes)

# 从真实序章到F夜间检查点，为失败与终局测试提供公共操作路径。
def reach_night_checkpoint(include_lullaby: bool = True) -> GameSession:
    # 开始一局独立游戏。
    session = new_session()
    # 玩家自己拔剑，初始安全快照应在A产生。
    interact_with(session, "sword")
    # 离开安全位后自己跨滑落口进入B。
    cross(session, "a_slide")
    # 两个箱子都实际探索并领取。
    interact_with(session, "score_time")
    # 彩蛋不作为主线必要条件，另有无彩蛋路线测试。
    if include_lullaby:
        # 可选谱由显式测试路线决定，产品不自动发放。
        interact_with(session, "score_lullaby")
    # 成年从普通货路到C。
    cross(session, "b_cargo")
    # 只从指定南侧站位推动唯一货运箱。
    interact_with(session, "cargo_box")
    # 动画推进真实箱子到凹位。
    advance(session, session.rules.box_seconds + 0.01)
    # 回到剑台使用已经开通的货运门。
    cross(session, "c_a")
    # 插剑变回孩童，昼夜不应改变。
    interact_with(session, "sword")
    # 少年可用窄门回B。
    cross(session, "a_child")
    # 唯一原创时间曲切夜。
    play(session, "time_shift")
    # 所有后续路段都由真实门槛能力通过。
    cross(session, "b_gate")
    # 夜间闸门才允许到E。
    cross(session, "d_e")
    # 正确洞口只由孩童进入F。
    cross(session, "drain_tracks")
    # 返回真实已保存的夜间安全点会话。
    return session
