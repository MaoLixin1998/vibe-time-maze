# 业务组件各自持有状态，会话只协调公开能力。
from time_maze.model.player import Player
# 年龄与全局昼夜不依赖设备或真实日期。
from time_maze.model.timeline import Timeline
# 动态货箱和门槛占用与静态地形分离。
from time_maze.model.maze_state import MazeState
# 鸡群负责时代独立行为及实际路径。
from time_maze.model.chicken_flock import ChickenFlock
# 地图定义为只读配置。
from time_maze.model.level_definition import LevelDefinition
# 规则定义为只读参数。
from time_maze.model.rules_definition import RulesDefinition
# 快照不向界面泄露内部容器。
from time_maze.model.game_snapshot import GameSnapshot
# 结果事件与声音发送游标分离。
from time_maze.model.game_event import GameEvent
# 邻格和距离只进行纯坐标计算。
from time_maze.model.movement import adjacent, distance, DIRECTION_STEPS
# 演奏只匹配离散音符及音区。
from time_maze.model.keyboard_rules import match_melody
# 门条件与玩家邻近提示始终共用判定。
from time_maze.model.transition_rules import portal_access
# 公开构造也经过纯内存实际边界，不能绕过包资源加载器。
from time_maze.model.level_validation import validate_definitions, require_finite_number
# 巢后安全入场条件独立维护，会话负责提交完整快照。
from time_maze.model.area_rules.nest_entry import is_safe_nest_entry
# 旷野胜利入口规则独立维护，会话仍拥有阶段与事件。
from time_maze.model.area_rules.meadow_entry import is_meadow_exit

# 最长一次追赶0.25秒，避免长卡顿突然跨完警告窗口。
MAX_CATCHUP_SECONDS = 0.25
# 子步不超过0.05秒，减少计时边界遗漏。
MAX_STEP_SECONDS = 0.05
# 有界事件历史防止长局不断积累展示数据。
EVENT_HISTORY_LIMIT = 64

# 本局协调器拥有阶段、检查点、领取记录和事件序号。
class GameSession:
    # 构造只创建纯业务状态，不启动窗口、音频或文件读取。
    def __init__(self, level: LevelDefinition, rules: RulesDefinition):
        # 只有明确模型类型才能进入本局，装载边界另校验字段。
        if not isinstance(level, LevelDefinition) or not isinstance(rules, RulesDefinition):
            # 不接收任意万能字典替代正式模型。
            raise ValueError("会话必须接收已校验地图和规则")
        # 验证内层不可变性、数值、ID及引用后整体接收配置。
        level, rules = validate_definitions(level, rules)
        # 已冻结配置只由只读属性导出。
        self._level = level
        # 世界效果始终使用同一规则来源。
        self._rules = rules
        # 货箱具有唯一所属区与指定北侧目标。
        cargo_entries = [(room.id, item) for room in level.rooms
                         # 不通过显示名称反推交互类型。
                         for item in room.objects if item.kind == "cargo_box"]
        # 缺少或重复重物不能建立真实回程。
        if len(cargo_entries) != 1 or cargo_entries[0][1].target_position is None:
            # 即使绕过加载器也不悄悄建立无效局。
            raise ValueError("会话需要唯一已定义终点的货箱")
        # 持有只读对象定义，不反写原地图。
        self._cargo_region, self._cargo = cargo_entries[0]
        # 声音发送序号不进入可回滚检查点。
        self._sequence = 0
        # 每次会话有自己独立事件列表。
        self._events = []
        # 本局初始状态由正式地图定义创建。
        self._reset_state()

    # 对外返回冻结地图配置。
    @property
    def level(self) -> LevelDefinition:
        # UI不会取得可变业务状态。
        return self._level

    # 对外返回冻结规则配置。
    @property
    def rules(self) -> RulesDefinition:
        # 曲谱展示与输入匹配共享同一来源。
        return self._rules

    # 重新建立本局状态，事件序号由调用者保留。
    def _reset_state(self) -> None:
        # 玩家从正式初始格开始，插值为完整格。
        self._player = Player(self._level.initial_region, self._level.initial_position,
                              # 移动以规则中的秒数推进。
                              self._rules.movement_seconds)
        # 孩童和白天是正式入口状态。
        self._timeline = Timeline()
        # 新局货箱与门占用不继承旧局。
        self._maze = MazeState()
        # 两时代鸡群都由本局独立创建。
        self._chickens = ChickenFlock(self._level, self._rules)
        # 正式序章必须由玩家先在剑台拔剑。
        self._phase = "intro"
        # 暂停只冻结模拟，不改变既有阶段。
        self._is_paused = False
        # 尚未实际跨出终局门槛。
        self._is_won = False
        # 开箱领奖不与迷宫胜利混为同一状态。
        self._reward_claimed = False
        # 个人谱册只有真实开箱后才收录。
        self._collected_scores = set()
        # 开启记录采用稳定谱箱ID。
        self._opened_chests = set()
        # 首次拔剑前没有可重试探索检查点。
        self._checkpoint = None
        # 门占用完整恢复值独立保存。
        self._checkpoint_thresholds = ()
        # 有限过场从零秒开始。
        self._phase_elapsed = 0.0
        # 滑落目标仅在真实迈出边界时登记。
        self._pending_portal = None
        # 最近反馈是正式玩家提示，不含拍摄对白。
        self._message = "走到剑台旁，按E拔剑开始探索"

    # 会话发送一次真实结果，历史有界且序号不回滚。
    def _emit(self, kind: str, detail: str = "") -> None:
        # 同一会话每个结果取得新序号。
        self._sequence += 1
        # 事件为不可变值，消费不能改变世界。
        self._events.append(GameEvent(self._sequence, kind, detail))
        # 丢弃最旧历史不改变序号意义。
        self._events = self._events[-EVENT_HISTORY_LIMIT:]

    # 操作只在可控阶段和完整落脚格执行。
    def _can_control(self) -> bool:
        # 演奏面板本身不冻结鸡，暂停与不可移动阶段才冻结输入。
        return (not self._is_paused and not self._player.is_moving
                # 通关后的reward仍允许移动和真实开箱。
                and self._phase in ("intro", "exploring", "reward"))

    # 当前门的结果与提示通过同一公开纯规则获得。
    def _portal_result(self, portal) -> tuple[bool, str]:
        # 门槛占用只针对实际当前区域与指定格。
        held = self._maze.is_threshold_held(self._player.region, portal.position)
        # 年龄、昼夜和货箱开通都是模型真实状态。
        return portal_access(portal, self._timeline.age, self._timeline.is_day,
                             # 被占用的夜间门允许安全离开。
                             self._maze.box_open, held)

    # 动态障碍格从独立货箱状态取得。
    def _is_box_tile(self, region: str, position: tuple[int, int]) -> bool:
        # 非货廊不存在这只共享重物。
        if region != self._cargo_region:
            # 地形不会因跨区错误阻挡。
            return False
        # 推开后的凹位仍真实占一格，但不阻断货路。
        box_position = self._cargo.target_position if self._maze.box_open else self._cargo.position
        # 仅物件实际占格阻挡，门开闭另判断。
        return position == box_position

    # 玩家请求一个完整格移动，返回是否真正提交。
    def move(self, direction: str) -> bool:
        # 只接受正式方向ID，不静默忽略非法控制映射。
        if type(direction) is not str or direction not in DIRECTION_STEPS:
            # 类型和范围都是公开输入边界。
            raise ValueError("移动方向必须为up/down/left/right")
        # 暂停、过场和未完成插值不会继续积累移动意图。
        if not self._can_control():
            # 拒绝表示没有位置变化。
            return False
        # 被墙挡住时转向仍可用于箱南侧朝北操作。
        self._player.face(direction)
        # 当前房间提供真实门槛和静态地形。
        room = self._level.room(self._player.region)
        # 只有站在门槛并朝出门方向走才跨区。
        for portal in room.portals:
            # 同一房间内其他方向输入仍是普通地板移动。
            if portal.position == self._player.position and portal.direction == direction:
                # 序章首先明确剑台真实操作。
                if self._phase == "intro":
                    # 不把开场拔剑偷换为自动年龄变化。
                    self._message = "先到剑台旁拔剑，再进入迷宫"
                    # 初始剧情入口尚未完成。
                    return False
                # 跨区必须通过同源实际条件。
                allowed, reason = self._portal_result(portal)
                # 显示真实不可通行原因。
                if not allowed:
                    # 不传送或弹到另一处安全点。
                    self._message = reason
                    # 原位置保留。
                    return False
                # 滑落只在真正迈出指定边界后触发有限过场。
                if portal.kind == "slide":
                    # 原区位置保持到过场结束。
                    self._phase = "sliding"
                    # 新滑落开始计时，不能重播未完成过程。
                    self._phase_elapsed = 0.0
                    # 保存唯一已经验证的目标。
                    self._pending_portal = portal
                    # 结果可供基础表现播放，不新增地图。
                    self._emit("slide_started", portal.id)
                    # 正式迈出动作已接受。
                    return True
                # 普通跨门立即提交合法区域落脚。
                self._cross_portal(portal)
                # 真实跨门已发生。
                return True
        # 普通格移动不会凭空产生跨区连接。
        target = adjacent(self._player.position, direction)
        # 静态墙与唯一货箱共同限制移动。
        if target not in room.floors or self._is_box_tile(room.id, target):
            # 箱子附近提示真实动作而非允许穿过。
            self._message = "前方重物挡路，成年站在南侧朝北按E推动" if self._is_box_tile(room.id, target) else "前方是墙"
            # 不建立穿墙插值。
            return False
        # 闭合门槛格不能从完整地面踩入。
        for portal in room.portals:
            # 当前门槛即将被占用时检查其真实开闭。
            if portal.position == target:
                # 占用放行仅对之前已站立格有效。
                allowed, reason = self._portal_result(portal)
                # 闭合门不撤地面，但阻止新占用。
                if not allowed:
                    # 提示与跨门条件一致。
                    self._message = reason
                    # 位置保持完整旧格。
                    return False
        # 提交碰撞格并开始画面插值。
        self._player.move_to(target)
        # 离开夜闸门槛后才真正解除延迟关闭。
        self._maze.release_unused(room.id, target)
        # 普通移动没有虚假交互结果。
        self._message = ""
        # 新格已经提交。
        return True

    # 合格跨门更新状态；最终出口才创建真正胜利。
    def _cross_portal(self, portal) -> None:
        # 合法目标落脚已在正式数据边界验证。
        self._player.place(portal.target_region, portal.target_position)
        # 不保留另一个区域无人占用的延迟关闭。
        self._maze.release_unused(self._player.region, self._player.position)
        # 白天通过仍被占用的夜闸后，目标门槛也须允许离开。
        if portal.condition == "night" and self._timeline.is_day:
            # 只延迟当前实际占用的一侧。
            self._maze.hold_threshold(self._player.region, self._player.position)
        # 真正F至G跨门是唯一迷宫胜利触发。
        if is_meadow_exit(portal):
            # 先记胜利，再播放出口过场。
            self._is_won = True
            # 鸡不会跟入G或阻断奖励。
            self._chickens.stop_chasing(self._timeline.age)
            # 有限出口展示结束后才恢复操作。
            self._phase = "exit_reveal"
            # 刚跨门开始爬出和展开展示。
            self._phase_elapsed = 0.0
            # 一次跨门只发送一次胜利结果。
            self._emit("won", portal.target_region)
            # 不在此时自动发奖或冻结领奖。
            self._message = "已走出迷宫，正在展开旷野"
        # 其他跨门属于正常探索。
        else:
            # 操作阶段继续保持探索。
            self._phase = "exploring"
            # 到达反馈使用静态区域名称。
            self._message = self._level.room(self._player.region).name
            # 夜间孩童安全进入F保存真实当前格完整检查点。
            if is_safe_nest_entry(self._player.region, self._timeline.age, self._timeline.is_day):
                # 夜间立即解除激活时代的追逐状态。
                self._chickens.on_timeline_changed(self._timeline.age, False)
                # 没有暗中将入口坐标改成门前。
                self._save_checkpoint()

    # 邻近正式物件交互；返回稳定结果ID。
    def interact(self) -> str:
        # 不可移动阶段无法重复启动动画或领奖。
        if not self._can_control():
            # 结果明确没有交互变化。
            return "busy"
        # 当前房间物件定义与运行状态分离。
        room = self._level.room(self._player.region)
        # 至多一个邻近目标优先按距离选择。
        nearby = sorted((item for item in room.objects
                         # 正交一格以内允许与动态物交互。
                         if distance(item.position, self._player.position) <= 1),
                        # 最近对象优先，ID作为确定性同距顺序。
                        key=lambda item: (distance(item.position, self._player.position), item.id))
        # 鸡巢没有额外未授权交互。
        for item in nearby:
            # 剑台是唯一年龄切换点。
            if item.kind == "sword":
                # 切龄不允许非法落脚；剑台附近本来是完整安全格。
                self._timeline.toggle_age()
                # 切龄保持当前昼夜，鸡只激活自己的时代状态。
                self._chickens.on_timeline_changed(self._timeline.age, self._timeline.is_day)
                # 正式首拔完成后开始探索。
                was_intro = self._phase == "intro"
                # 之后插拔剑仍属于正常探索能力。
                self._phase = "exploring"
                # 真正年龄变化发送结果。
                self._emit("age_changed", self._timeline.age)
                # 年份与显示属于年龄映射。
                self._message = f"当前是{self._timeline.year}年"
                # 首次拔剑保存成年A安全探索状态。
                if was_intro:
                    # 完整检查点不回滚声音发送序号。
                    self._save_checkpoint()
                # 与UI事件使用同一稳定结果ID。
                return "age_changed"
            # 两只谱箱通过同一真实领取能力。
            if item.kind == "score":
                # 已开箱不重复收录或发结果。
                if item.id in self._opened_chests:
                    # 查询已领取时只更新反馈。
                    self._message = "这只谱箱已经打开，可在随身谱册反复查阅"
                    # 不触发新的领取事件。
                    return "already_collected"
                # 记录箱和曲谱一起提交，避免半领取状态。
                self._opened_chests.add(item.id)
                # 收录跨年龄和昼夜保留。
                self._collected_scores.add(item.payload)
                # 结果详情是正式谱ID。
                self._emit("score_collected", item.payload)
                # 可读反馈不用决定规则。
                self._message = "曲谱已收入随身谱册"
                # 真实交互成功。
                return "score_collected"
            # 货箱必须由成年在C侧从下方朝北操作。
            if item.kind == "cargo_box":
                # 开通后原格不再有可重复推动的箱。
                if self._maze.box_open:
                    # 已停入凹位的反馈不重置通路。
                    self._message = "货路已经开通"
                    # 重复操作没有结果变化。
                    return "already_open"
                # 孩童不能推重物也不能穿过它。
                if self._timeline.age != "adult":
                    # 明确年龄能力边界。
                    self._message = "重物太重，需要成年推动"
                    # 不开始无效动画。
                    return "requires_adult"
                # 指定方向和唯一终点避免自由推错造成软锁。
                if self._player.position != adjacent(item.position, "down") or self._player.direction != "up":
                    # 与真实站位要求相同。
                    self._message = "站在重物南侧，朝北推动"
                    # 重物仍占原格。
                    return "requires_push_position"
                # 原地有限推移动画期间暂停其他输入。
                self._phase = "pushing"
                # 一次动画从零计时。
                self._phase_elapsed = 0.0
                # 起推只发送一次结果。
                self._emit("box_started", item.id)
                # 正式动画是玩家真实操作带来的变化。
                self._message = "正在向北推入墙边凹位"
                # 成功启动不等于已经开通。
                return "box_started"
            # 通关后恢复G操作才允许邻近开箱领奖。
            if item.kind == "reward" and self._phase == "reward":
                # 每局只允许领取一次。
                if self._reward_claimed:
                    # 已领取不重新生成奖品。
                    self._message = "奖励已经领取"
                    # 重复查询明确反馈。
                    return "already_claimed"
                # 领取状态与事件原子提交。
                self._reward_claimed = True
                # 固定产品奖励ID不携带视频对白。
                self._emit("reward_claimed", item.payload)
                # 正式奖励反馈保持可读。
                self._message = "已获得主机与游戏"
                # 真实领取完成。
                return "reward_claimed"
        # 探索鸡領地时E交互可表达近距挥剑挑衅。
        if self._phase == "exploring" and self._chickens.provoke(self._timeline.age, room.id,
                                                                # 与演奏鸡回应是不同能力。
                                                                self._player.position, self._timeline.is_day):
            # 鸡先警告，绝不跳过反应窗口。
            self._emit("chicken_warning", room.id)
            # 挑衅结果只提示已经发生的规则。
            self._message = "鸡正在鸣叫警告"
            # 可供声音适配消费。
            return "chicken_warning"
        # 没有物件不会在世界中制造新效果。
        self._message = "附近没有可交互物件"
        # UI能清楚区别无目标与成功。
        return "nothing"

    # 完整乐器提交只按已校验序列匹配，不依赖实际音频。
    def play_keyboard(self, note_events: tuple[tuple[int, int], ...]) -> str:
        # 参数类型、音符和八度在无副作用匹配阶段验证。
        melody = match_melody(note_events, self._rules)
        # 仅探索完整落脚格接受世界效果。
        if not self._can_control() or self._phase != "exploring":
            # 暂停及过场不会补接演奏。
            return "busy"
        # 未完成和未匹配不改变世界。
        if melody is None:
            # 反馈错音不触发随机惩罚。
            self._message = "短句尚未匹配，请检查音符与八度后重新提交"
            # 无状态效果的稳定结果。
            return "unmatched"
        # 唯一主线原创曲每次合法命中切换相位。
        if melody.effect == "toggle_day":
            # 夜门上由夜切昼时先保留当前安全占用。
            if not self._timeline.is_day:
                # 只检查真正站着的门槛，不随意保留整区门。
                for portal in self._level.room(self._player.region).portals:
                    # 夜闸即将关闭但不能弹出当前占用者。
                    if portal.condition == "night" and portal.position == self._player.position:
                        # 下一步离开时才释放该门状态。
                        self._maze.hold_threshold(self._player.region, self._player.position)
            # 地面和年龄不改变，当前落脚仍合法。
            self._timeline.toggle_day()
            # 激活时代鸡立即停追归巢或按白天唤醒。
            self._chickens.on_timeline_changed(self._timeline.age, self._timeline.is_day)
            # 稳定发送本次唯一相位结果。
            self._emit("day_changed", "day" if self._timeline.is_day else "night")
            # 同一原创谱可从白天切夜，也可从夜切昼。
            self._message = "已切换为白天" if self._timeline.is_day else "已切换为夜晚"
        # 摇篮彩蛋只提供可见结果，不改变通关或世界状态。
        elif melody.effect == "egg_lullaby":
            # 有无谱册都不限制玩家主动演奏。
            self._emit("egg_lullaby", melody.id)
            # 灰盒先提供真实可见反馈。
            self._message = "摇篮曲彩蛋：熟悉的旋律响起"
        # 原创鸡回应不升级追逐或改写时代状态。
        elif melody.effect == "chicken_call":
            # 仅附近有鸡时回应结果属真实发生。
            responded = self._chickens.respond_to_call(self._timeline.age, self._player.region)
            # 同一音符仍是笛音，鸡声只是结果事件。
            self._emit("chicken_call", "nearby" if responded else "distant")
            # 远处也有清楚无副作用反馈。
            self._message = "附近的鸡回应了短句" if responded else "短句响起，附近没有鸡"
        # 返回真实效果ID，不用显示文字反推。
        return melody.effect

    # 暂停边界只接受真实布尔值，失焦可复用该能力。
    def set_paused(self, is_paused: bool) -> None:
        # 不接受数字一代替布尔值。
        if type(is_paused) is not bool:
            # 界面映射错误清晰报出。
            raise ValueError("暂停参数必须为bool")
        # 暂停不重置过场或玩家坐标。
        self._is_paused = is_paused

    # 保存完整业务检查点，临时音符前缀与声音游标不回滚。
    def _save_checkpoint(self) -> None:
        # 当前实际合法格直接保存，不移到门前。
        self._checkpoint = self.snapshot()
        # 门槛占用是运行状态，也须完整保存。
        self._checkpoint_thresholds = self._maze.threshold_snapshot()
        # 清楚区分保存发生与猜测存在。
        self._emit("checkpoint_saved", self._player.region)

    # 秒数非负有限；大卡顿受控追赶，不把现实时间全算成追逐。
    def update(self, seconds: float) -> None:
        # 巨量整数、bool、非法类型和非有限值统一在无副作用边界拒绝。
        elapsed_seconds = require_finite_number(seconds)
        # 合法有限秒数仍不能倒退模拟时间。
        if elapsed_seconds < 0.0:
            # 不通过回退成零吞掉错误。
            raise ValueError("时间步必须为有限非负秒")
        # 暂停和失败不会推进世界或过场。
        if self._is_paused or self._phase == "failed":
            # 保持完整快照。
            return
        # 上限限制一次调用的追赶秒数。
        remaining = min(elapsed_seconds, MAX_CATCHUP_SECONDS)
        # 每次子步都保持警告与碰撞计时顺序。
        while remaining > 0.0:
            # 子步上限降低计时边界漂移。
            step = min(remaining, MAX_STEP_SECONDS)
            # 玩家位置插值只在该受控时间步推进。
            self._player.update(step)
            # 有限过场独立于鸡模拟。
            if self._phase in ("sliding", "pushing", "exit_reveal"):
                # 不可移动阶段不让鸡偷走玩家反应窗口。
                self._advance_cutscene(step)
            # 演奏面板没有改变阶段，探索始终推进鸡群。
            elif self._phase == "exploring":
                # 鸡行为读取当前真实年龄、昼夜和位置。
                warned, caught = self._chickens.update(step, self._timeline.age,
                                                       # 未激活时代不模拟也不继承仇恨。
                                                       self._timeline.is_day, self._player.region,
                                                       # 逻辑格用于实际捕获判定。
                                                       self._player.position)
                # 新警告才发送一次声音结果。
                if warned:
                    # 多只同时警告仍表示一次本步反馈。
                    self._emit("chicken_warning", self._player.region)
                    # 清楚提醒仍有完整窗口。
                    self._message = "鸡正在鸣叫警告，准备撤离"
                # 捕获触发失败而非移动到其他区。
                if caught:
                    # 失败阶段冻结之后模拟。
                    self._phase = "failed"
                    # 明确显示正式重试能力。
                    self._message = "被鸡捕获，按R恢复最近完整检查点"
                    # 真正失败发送一次结果。
                    self._emit("failed", self._player.region)
                    # 本次调用剩余时间不会继续追逐。
                    return
            # 减去真实已处理秒数。
            remaining = max(0.0, remaining - step)

    # 有限过场状态推进，渲染不自行发奖或改变阶段。
    def _advance_cutscene(self, seconds: float) -> None:
        # 只累加已验证受控时间。
        self._phase_elapsed += seconds
        # 推箱到唯一终点才开通通路。
        if self._phase == "pushing":
            # 归一化进度由模型供图形表现。
            self._maze.set_box_progress(min(1.0, self._phase_elapsed / self._rules.box_seconds))
            # 开通时动画有限结束。
            if self._maze.box_open:
                # 重新允许正常探索。
                self._phase = "exploring"
                # 货路跨年龄和昼夜共享保留。
                self._emit("box_opened", self._cargo.id)
                # 不额外移动角色或新增阻挡。
                self._message = "货路已开通，两龄昼夜均可通行"
        # 滑落结束才到B合法落脚。
        elif self._phase == "sliding" and self._phase_elapsed >= self._rules.slide_seconds:
            # 已保存目标来自真实迈出边界的门。
            portal = self._pending_portal
            # 有目标才能完成真实过场。
            if portal is None:
                # 内部契约错误不能伪装成功。
                raise RuntimeError("滑落缺少合法目标")
            # 跨区位置与普通门使用同一能力。
            self._cross_portal(portal)
            # 过场结束清除待办引用，避免再次播放。
            self._pending_portal = None
            # 保留一次真实落地结果。
            self._emit("slide_finished", portal.id)
        # 出口过场结束后恢复G内合法操作。
        elif self._phase == "exit_reveal" and self._phase_elapsed >= self._rules.exit_seconds:
            # 与跳过使用同一正常完成路径。
            self._finish_exit()

    # 正常结束与跳过都落在相同合法格、保留未领奖状态。
    def _finish_exit(self) -> None:
        # 出口只有一次有限展示阶段。
        self._phase = "reward"
        # 最终进度为完整结束。
        self._phase_elapsed = self._rules.exit_seconds
        # 不在过场中自动开启奖励箱。
        self._message = "旷野已展开，走近宝箱按E领取奖励"
        # 结果供表现解除过场覆盖。
        self._emit("cutscene_finished", "exit_reveal")

    # 跳过仅作用于正式出口有限过场。
    def skip_cutscene(self) -> None:
        # 暂停时不会绕过冻结推进阶段。
        if not self._is_paused and self._phase == "exit_reveal":
            # 使用正常结束路径，避免两种结果不一致。
            self._finish_exit()

    # 失败重试恢复完整最近安全检查点，返回是否真正恢复。
    def retry(self) -> bool:
        # R不作为任意位置免费传送。
        if self._phase != "failed" or self._checkpoint is None:
            # 探索中的R没有业务副作用。
            return False
        # 保存值为本局创建的冻结快照。
        saved = self._checkpoint
        # 区域和真实格一起恢复。
        self._player.place(saved.region, saved.pos)
        # 年龄与昼夜成组还原。
        self._timeline.restore(saved.age, saved.is_day)
        # 货箱与门占用完整还原。
        self._maze.restore(saved.box_open, saved.box_progress, self._checkpoint_thresholds)
        # 两时代鸡位置、模式、计时均还原。
        self._chickens.restore(saved.chicken_state)
        # 收录记录重新建立自有集合。
        self._collected_scores = set(saved.collected_scores)
        # 已开箱状态与谱一起恢复。
        self._opened_chests = set(saved.opened_chests)
        # 安全检查点只属于可探索阶段。
        self._phase = saved.phase
        # 失败解除后不继承暂停。
        self._is_paused = False
        # 业务胜利也属于完整快照。
        self._is_won = saved.is_won
        # 奖励状态与胜利独立恢复。
        self._reward_claimed = saved.reward_claimed
        # 检查点不保存正在播放的移动或过场。
        self._phase_elapsed = 0.0
        # 失败前待办过场不能复活。
        self._pending_portal = None
        # 恢复反馈不重放已发生结果。
        self._message = "已恢复完整安全检查点"
        # 序号递增而非从saved.events复写。
        self._emit("retried", saved.region)
        # 真实恢复完成。
        return True

    # 完整重开与失败重试不同，回到正式孩童白天入口。
    def restart(self) -> None:
        # 创建全部独立初始状态，不复用旧局可变对象。
        self._reset_state()
        # 新开始保留会话发送序号，声音消费不会漏掉。
        self._emit("restarted", "A")

    # 归一化过场进度是只读展示值。
    def _cutscene_progress(self) -> float:
        # 不同正式过场使用各自有限时长。
        duration = {"sliding": self._rules.slide_seconds, "pushing": self._rules.box_seconds,
                    # 出口正常结束后保持完整进度。
                    "exit_reveal": self._rules.exit_seconds}.get(self._phase)
        # 普通探索没有活跃过场。
        if duration is None:
            # G领奖阶段已展示完出口。
            return 1.0 if self._phase == "reward" else 0.0
        # 限定边界防止展示越界。
        return min(1.0, self._phase_elapsed / duration)

    # 邻近提示从真实交互定义和门条件生成。
    def _nearby_hint(self) -> str:
        # 只读取当前位置的静态定义。
        room = self._level.room(self._player.region)
        # 邻近动态物件展示可执行用途。
        for item in room.objects:
            # 只有正交一格内显示实际操作提示。
            if distance(item.position, self._player.position) <= 1:
                # 剑台表示年龄切换能力。
                if item.kind == "sword":
                    # 当前年龄决定插拔用途，不改变同一接口。
                    return "E：拔剑变成年" if self._timeline.age == "child" else "E：插剑恢复孩童"
                # 谱箱提示不会直接发完整谱。
                if item.kind == "score":
                    # 已领取由实际记录决定。
                    return "已收录：打开K查看谱册" if item.id in self._opened_chests else "E：打开曲谱宝箱"
                # 货箱提示与成年及实际方向一致。
                if item.kind == "cargo_box" and not self._maze.box_open:
                    # 不把箱上文字视为能够通行。
                    return "E：成年从南侧朝北推动重物"
                # 奖励箱仅在可操作G阶段领取。
                if item.kind == "reward":
                    # 领取一次，不因胜利已记而冻结。
                    return "奖励已领取" if self._reward_claimed else "E：打开奖励宝箱"
        # 门附近用途提示与通行查询完全共源。
        for portal in room.portals:
            # 查看用途不限于站到闭合门格。
            if distance(portal.position, self._player.position) <= 1:
                # 取真实当前条件结果，避免渲染写另一套规则。
                return self._portal_result(portal)[1]
        # 不在未知位置泄露正确排水口答案。
        return ""

    # 导出独立只读快照；查询不推进世界、读文件或发事件。
    def snapshot(self) -> GameSnapshot:
        # 货箱从原格向正式目标插值，渲染不捏造停放位置。
        box_pos = tuple(start + (end - start) * self._maze.box_progress
                        # 与真实推物终点保持同一来源。
                        for start, end in zip(self._cargo.position, self._cargo.target_position))
        # 全部嵌套集合在边界冻结为元组。
        return GameSnapshot(self._player.region, self._player.position, self._player.visual_position,
                            # 年份从年龄映射，昼夜全局一致。
                            self._timeline.age, self._timeline.year, self._timeline.is_day,
                            # 展示流程与胜利及领奖各有明确值。
                            self._phase, self._is_paused, self._is_won, self._reward_claimed,
                            # 货箱开通状态与插值进度同源。
                            self._maze.box_open, self._maze.box_progress,
                            # 随身谱和箱记录按ID排序使比对可复现。
                            tuple(sorted(self._collected_scores)), tuple(sorted(self._opened_chests)),
                            # 当前时代展示与两时代完整恢复值分开。
                            self._chickens.visible_snapshot(self._timeline.age), self._chickens.snapshot(),
                            # 事件列表不暴露内部可变容器。
                            tuple(self._events), self._message, self._nearby_hint(),
                            # 正式过场进度仅供显示。
                            self._cutscene_progress(), self._cargo_region, box_pos,
                            # 当前实际占用夜门是完整业务展示值。
                            self._maze.threshold_snapshot())
