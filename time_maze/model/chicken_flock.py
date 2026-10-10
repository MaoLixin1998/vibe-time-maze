# 鸡的路径是纯内存地图计算，不实体占用玩家通路。
from time_maze.model.movement import chicken_path, distance
# 地图只读注入，不被鸡行为改写。
from time_maze.model.level_definition import LevelDefinition
# 警告和移动时长从已校验规则取得。
from time_maze.model.rules_definition import RulesDefinition
# 行为秒数及恢复计时共用严格的有限浮点边界。
from time_maze.model.level_validation import require_finite_number
# 鸡与玩家使用同一不可变格坐标边界。
from time_maze.model.movement import validate_position

# 两时代各自持有鸡位置、警戒及计时，不继承另一个时代的仇恨。
class ChickenFlock:
    # 从独立巢对象建立本局的两套状态。
    def __init__(self, level: LevelDefinition, rules: RulesDefinition):
        # 组件公开构造只接受明确地图及规则类型。
        if type(level) is not LevelDefinition or type(rules) is not RulesDefinition:
            # 不把任意对象当作行为配置。
            raise ValueError("鸡群需要正式地图与规则")
        # 只读地图可供路径查询共享。
        self._level = level
        # 行为参数与声音无关。
        self._rules = rules
        # 每只鸡的家为区域及格坐标。
        self._homes = tuple((room.id, *item.position)
                            # 全部定义都是已校验不可变值。
                            for room in level.rooms for item in room.objects if item.kind == "nest")
        # 白天初始展示两个前院巡守和一只巢内鸡。
        starts = level.chicken_spawns or self._homes
        # 鸡出生点和巢必须一一对应，避免隐含截断。
        if len(starts) != len(self._homes):
            # 声明数量错误在构造时拒绝。
            raise ValueError("鸡出生点与巢数量不一致")
        # 各年龄字典中的列表分别创建，绝不共享可变个体。
        self._states = {age: [[*starts[index], "idle", 0.0]
                              # 个体数据为region、x、y、mode、剩余计时。
                              for index in range(len(self._homes))]
                        # 两时代只有定义共享，行为不共享。
                        for age in ("child", "adult")}

    # 当前时代查询与变更统一验证明确年龄ID。
    def _validate_age(self, age: str) -> None:
        # 不把显示年份或bool当作年龄能力。
        if type(age) is not str or age not in ("child", "adult"):
            # 公开调用保留ValueError契约。
            raise ValueError("鸡群年龄必须为child或adult")

    # 领地行为读取的玩家上下文必须是实际合法格。
    def _validate_context(self, age: str, is_day: bool,
                          region: str, position: tuple[int, int]) -> None:
        # 年龄选择正确独立状态组。
        self._validate_age(age)
        # 昼夜是全局真布尔值，不靠bool()转换。
        if type(is_day) is not bool or type(region) is not str:
            # 非法参数不触发新警告。
            raise ValueError("鸡群上下文类型非法")
        # 玩家格不允许外部可变引用。
        validate_position(position)
        # 领地判断只在真正地板执行。
        if position not in self._level.room(region).floors:
            # 无地板坐标不能成为路径目标。
            raise ValueError("鸡群玩家格不合法")

    # 昼夜和年龄变动只协调当前激活时代。
    def on_timeline_changed(self, age: str, is_day: bool) -> None:
        # 不接受未知时代或非法相位参数。
        self._validate_age(age)
        # 公共变更只接收真正昼夜状态。
        if type(is_day) is not bool:
            # 非法输入不清除追逐。
            raise ValueError("鸡群昼夜必须为bool")
        # 非激活时代保留自身状态。
        for index, chicken in enumerate(self._states[age]):
            # 夜间立即解除警告或追逐，沿真实路径返巢。
            if not is_day:
                # 已在巢里的鸡无需再移动。
                chicken[3] = "sleeping" if tuple(chicken[:3]) == self._homes[index] else "returning"
                # 清空旧白天追逐计时。
                chicken[4] = 0.0
            # 切白天只唤醒夜间行为，不重置已经存在的白天追逐。
            elif chicken[3] in ("returning", "sleeping"):
                # 领地判断会在下一受控时间步给出警告。
                chicken[3] = "idle"
                # 新警告计时不会继承半截归巢时间。
                chicken[4] = 0.0

    # 正常演奏鸡回应不创造或升级追逐状态。
    def respond_to_call(self, age: str, region: str) -> bool:
        # 年龄查询不得隐式创建另一组状态。
        self._validate_age(age)
        # 先核验区域确实存在于正式地图。
        self._level.room(region)
        # 只在有附近鸡时返回真实回应。
        return any(chicken[0] == region for chicken in self._states[age])

    # 邻近挥剑挑衅仍先完整警告，不直接将玩家抓住。
    def provoke(self, age: str, region: str, position: tuple[int, int], is_day: bool) -> bool:
        # 所有上下文先通过边界，再开始任何警戒变更。
        self._validate_context(age, is_day, region, position)
        # 夜间挑衅不破坏停追和归巢规则。
        if not is_day:
            # 返回没有触发警告。
            return False
        # 同区域近距离鸡逐只判断。
        started = False
        # 个体状态归该时代所有。
        for chicken in self._states[age]:
            # 距离两格内且未警戒的鸡才开始新警告。
            if chicken[0] == region and distance(tuple(chicken[1:3]), position) <= 2 and chicken[3] == "idle":
                # 先鸣叫，模式不是直接追逐。
                chicken[3] = "warning"
                # 从完整警告秒数开始倒计时。
                chicken[4] = self._rules.warning_seconds
                # 告知会话发送一次警告事件。
                started = True
        # 不重复警告已经警戒的鸡。
        return started

    # 受控时间步返回警告是否新发生及是否被实际捕获。
    def update(self, seconds: float, age: str, is_day: bool,
               player_region: str, player_position: tuple[int, int]) -> tuple[bool, bool]:
        # 先统一核验类型、非有限值和巨大整数表示溢出。
        seconds = require_finite_number(seconds)
        # 不允许负时间延长或回滚追逐窗口。
        if seconds < 0.0:
            # 无效时间不会破坏个体计时。
            raise ValueError("鸡群时间步必须为有限非负秒")
        # 上下文也在受控变更前核验。
        self._validate_context(age, is_day, player_region, player_position)
        # 返回值只表达本次真实结果。
        warned = False
        # 捕获在当前激活时代判断。
        caught = False
        # 玩家位置转换为与路径节点相同的结构。
        goal = (player_region, *player_position)
        # 鸡的时代状态独立推进。
        for index, chicken in enumerate(self._states[age]):
            # 当前鸡所在区域决定可用地板和领地。
            room = self._level.room(player_region)
            # 白天进入领地才开始警告；已离开外围的鸡不无理由袭击。
            if is_day and chicken[3] == "idle" and chicken[0] == player_region and player_position in room.territory:
                # 进入领地的真实时刻开始警告。
                chicken[3] = "warning"
                # 足额窗口保障面板输入后仍有反应机会。
                chicken[4] = self._rules.warning_seconds
                # 声音消费只接收一次新警告。
                warned = True
            # 警告始终先于追逐。
            if chicken[3] == "warning":
                # 警告按真实模拟时间推进。
                chicken[4] = max(0.0, chicken[4] - seconds)
                # 计时到期后再切追逐。
                if chicken[4] == 0.0:
                    # 新追逐先等一个移动间隔。
                    chicken[3] = "chasing"
                    # 不在计时结束的同一瞬间瞬移抓人。
                    chicken[4] = self._rules.chicken_step_seconds
            # 只有返巢和追逐模式会走格子。
            elif chicken[3] in ("chasing", "returning"):
                # 剩余秒数允许在子步边界中稳定推进。
                chicken[4] = max(0.0, chicken[4] - seconds)
                # 到间隔边界才提交下一真实格位。
                if chicken[4] == 0.0:
                    # 归巢和追逐分别使用自己的目标。
                    target = self._homes[index] if chicken[3] == "returning" else goal
                    # 玩家离开E/F后鸡不能穿过夜闸追进其他区。
                    path = chicken_path(self._level, tuple(chicken[:3]), target)
                    # 路径有下一格时只走一步，绝不穿墙瞬移。
                    if len(path) > 1:
                        # 保留行为和计时，只更新真实坐标。
                        chicken[:3] = path[1]
                    # 返回速度独立于追逐速度。
                    chicken[4] = (self._rules.return_step_seconds if chicken[3] == "returning"
                                  # 追逐间隔给玩家至少同量级移动机会。
                                  else self._rules.chicken_step_seconds)
                    # 抵达自己巢后才睡，不在排水口凭空消失。
                    if chicken[3] == "returning" and tuple(chicken[:3]) == self._homes[index]:
                        # 下次白天唤醒保持同一巢位置。
                        chicken[3] = "sleeping"
                        # 睡眠没有需要推进的行为计时。
                        chicken[4] = 0.0
            # 捕获只在白天真实追逐及同一格发生。
            if is_day and chicken[3] == "chasing" and tuple(chicken[:3]) == goal:
                # 与玩家碰撞只触发失败，不实体堵路。
                caught = True
        # 会话负责事件发送及失败流程。
        return warned, caught

    # 通关立即结束本轮普通追逐，不允许鸡进入G。
    def stop_chasing(self, age: str) -> None:
        # 查询目标时代必须真实存在。
        self._validate_age(age)
        # 当前时代的全部警戒模式都停止。
        for chicken in self._states[age]:
            # 保留位置供必要展示，停止捕获。
            chicken[3] = "idle"
            # 消除待发生追逐计时。
            chicken[4] = 0.0

    # 当前时代展示数据全部转换为嵌套不可变值。
    def visible_snapshot(self, age: str) -> tuple:
        # 展示查询同样明确所属时代。
        self._validate_age(age)
        # 不将内部列表交给渲染。
        return tuple(tuple(chicken[:4]) for chicken in self._states[age])

    # 完整检查点包含两个时代位置、行为和计时。
    def snapshot(self) -> tuple:
        # 固定年龄顺序便于比对恢复是否完整。
        return tuple((age, tuple(tuple(chicken) for chicken in self._states[age]))
                     # 不用浅拷贝泄露嵌套列表。
                     for age in ("child", "adult"))

    # 从本局不可变检查点创建新的私有个体列表。
    def restore(self, states: tuple) -> None:
        # 外层只能是完整不可变二时代值。
        if type(states) is not tuple or len(states) != 2:
            # 不接受部分时代恢复。
            raise ValueError("鸡群恢复需要完整两个时代")
        # 所有数据先核验进入新容器，成功前不修改当前鸡群。
        checked = {}
        # 两时代逐项核验。
        for entry in states:
            # 每时代有年龄与个体元组两项。
            if type(entry) is not tuple or len(entry) != 2:
                # 不从任意可变列表解包。
                raise ValueError("鸡群恢复时代结构非法")
            # 已确认结构后拆分值。
            age, chickens = entry
            # 年龄与实际状态组保持一致。
            self._validate_age(age)
            # 不接受重复时代、缺鸡或可变个体容器。
            if age in checked or type(chickens) is not tuple or len(chickens) != len(self._homes):
                # 数量必须与静态巢对应。
                raise ValueError("鸡群恢复时代重复或个体数量非法")
            # 本时代新列表仅在全部校验后整体替换。
            values = []
            # 每鸡完整节点、模式、剩余计时都属于恢复值。
            for chicken in chickens:
                # 个体含区域、x、y、模式和计时五项。
                if type(chicken) is not tuple or len(chicken) != 5:
                    # 少字段不得用默认计时覆盖。
                    raise ValueError("鸡群恢复个体结构非法")
                # 鸡活动只允许E与F真实通道。
                if type(chicken[0]) is not str or chicken[0] not in ("E", "F"):
                    # G不存在普通追逐鸡。
                    raise ValueError("鸡群恢复区域非法")
                # 坐标继续沿用不可变格边界。
                position = validate_position(chicken[1:3])
                # 不能将鸡恢复到墙内。
                if position not in self._level.room(chicken[0]).floors:
                    # 恢复不是瞬移容错。
                    raise ValueError("鸡群恢复格无地板")
                # 模式只允许实际实现的五种行为。
                if type(chicken[3]) is not str or chicken[3] not in ("idle", "warning", "chasing", "returning", "sleeping"):
                    # 未知模式不能默默变idle。
                    raise ValueError("鸡群恢复模式非法")
                # 计时必须有限非负且不超过本局最长正式计时。
                limit = max(self._rules.warning_seconds, self._rules.chicken_step_seconds,
                            # 返巢计时也受同一有限边界。
                            self._rules.return_step_seconds)
                # 恢复计时也不能绕过严格有限数转换。
                timer = require_finite_number(chicken[4])
                # 所属模式计时范围必须符合本局规则。
                if not 0.0 <= timer <= limit:
                    # 不夹紧非法恢复计时。
                    raise ValueError("鸡群恢复计时非法")
                # 单只鸡创建自己的可变列表。
                values.append(list(chicken))
            # 一个时代全部通过才加入临时完整集合。
            checked[age] = values
        # 每次恢复重建列表，旧检查点不会被后来行为改写。
        self._states = checked
