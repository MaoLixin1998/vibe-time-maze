# 有限状态图使用标准队列和反向边。
from collections import deque, defaultdict
# 测试类仅覆盖静态状态可恢复性，不声称鸡群时序公平性。
import unittest
# 数据来自正式包而非制作图。
from time_maze.adapters.content_loader import load_content

# 从公开关卡声明独立枚举位置、年龄、昼夜和货运开通状态。
class TestTopology(unittest.TestCase):
    # 所有可达非终局抽象状态应能回剑台或进入G。
    def test_all_reachable_states_have_recovery(self) -> None:
        # 读取已校验静态定义，测试不修改原图。
        level, _, _ = load_content()
        # 双向四格移动采用独立规格增量。
        steps = ((0, -1), (0, 1), (-1, 0), (1, 0))
        # 起点是首次拔剑后的成年A安全状态。
        start = (level.initial_region, *level.initial_position, "adult", True, False)
        # 队列建立有限可达图。
        pending = deque([start])
        # 已访问节点不重复入队。
        visited = {start}
        # 反向边用于从安全／胜利节点检查全部状态可恢复。
        reverse = defaultdict(set)
        # 当前已确定规则只有有限布尔状态。
        while pending:
            # 每次扩展一个独立位置状态。
            current = pending.popleft()
            # 拆开坐标和机制值，不能从文字反推。
            region, x, y, age, is_day, is_open = current
            # G是终局，不新增通关后昼夜谜题。
            if region == "G":
                # 领奖玩法由完整会话测试验证。
                continue
            # 房间只读查询不会反写地板。
            room = level.room(region)
            # 候选首先包含同一原创曲的可逆时间切换。
            candidates = [(region, x, y, age, not is_day, is_open)]
            # 在静态完整地板上枚举移动，时序与插值另测。
            for dx, dy in steps:
                # 邻格必须是真实地板。
                if (x + dx, y + dy) in room.floors:
                    # 动态货箱独占一个格，初态和终态均不能穿过。
                    box = next((item for item in room.objects if item.kind == "cargo_box"), None)
                    # 非箱子格可作为静态图边。
                    if box is None or (x + dx, y + dy) != (box.target_position if is_open else box.position):
                        # 同区移动不改变时代、相位或箱状态。
                        candidates.append((region, x + dx, y + dy, age, is_day, is_open))
            # 门条件独立按已确定规格枚举，不调用被测portal_access。
            for portal in room.portals:
                # 只能在声明的同一门槛跨区。
                if portal.position != (x, y):
                    # 不能隔空从房间中心转移。
                    continue
                # 条件ID与用户确定的规则表对应。
                can_pass = {"open": True, "child": age == "child", "cargo": is_open,
                            "night": not is_day, "child_day": age == "child" and is_day}[portal.condition]
                # 合格条件才添加真实连接。
                if can_pass:
                    # 目标落脚来自正式数据。
                    candidates.append((portal.target_region, *portal.target_position, age, is_day, is_open))
            # 剑台邻近格允许切年龄，其他区域没有该能力。
            for item in room.objects:
                # 只把正交邻近格作为真实交互位置。
                if abs(item.position[0] - x) + abs(item.position[1] - y) > 1:
                    # 远处对象不能影响当前节点。
                    continue
                # 同一剑台切年龄，保留昼夜和箱状态。
                if item.kind == "sword":
                    # 年龄只在A合法站位切换。
                    candidates.append((region, x, y, "child" if age == "adult" else "adult", is_day, is_open))
                # 成年须从箱南侧施力才能开通，静态图合并有限推动过程。
                if item.kind == "cargo_box" and age == "adult" and (x, y) == (item.position[0], item.position[1] + 1):
                    # 开通是唯一共享机关例外。
                    candidates.append((region, x, y, age, is_day, True))
            # 记录每条真实有限状态边。
            for candidate in candidates:
                # 反向恢复搜索需要全部来源。
                reverse[candidate].add(current)
                # 新节点只扩展一次。
                if candidate not in visited:
                    # 先标记以防重复入队。
                    visited.add(candidate)
                    # 下一轮继续扩展。
                    pending.append(candidate)
        # A安全区与G胜利都属于可恢复目标。
        safe = {node for node in visited if node[0] in {"A", "G"}}
        # 从目标集合逆向找所有有恢复路线的状态。
        pending = deque(safe)
        # 已确认可恢复状态从安全集合开始。
        recoverable = set(safe)
        # 所有反向边有限，搜索必然结束。
        while pending:
            # 扩展一个已可恢复节点。
            current = pending.popleft()
            # 前驱只要到达它也可恢复。
            for previous in reverse[current]:
                # 避免重复访问同一状态。
                if previous not in recoverable:
                    # 新前驱被证明存在安全路线。
                    recoverable.add(previous)
                    # 继续向更早状态展开。
                    pending.append(previous)
        # 不仅检查一条最短通关线，所有可达非终局节点都应有恢复路径。
        self.assertEqual(visited - recoverable, set())
        # 检查图确实覆盖七区而非起点附近小子图。
        self.assertEqual({node[0] for node in visited}, set("ABCDEFG"))
        # 记录有限图规模，方便实际验收证据核对。
        print(f"静态抽象状态图: {len(visited)} 个可达状态全部可恢复")
