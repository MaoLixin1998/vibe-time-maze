# unittest只用于正式机制回归，不发现制作场景。
import unittest
# 冻结配置以新对象构造异常输入，不改写正式默认数据。
from dataclasses import replace
# 正式音符输入边界独立校验。
from time_maze.model.keyboard_rules import validate_notes
# 公开操作路径不穿透模型内部字段。
from support.tests.journey import new_session, advance, walk_to, cross, interact_with, play, reach_night_checkpoint

# 一份测试类围绕完整会话状态不变量，遵守单类单文件。
class TestSession(unittest.TestCase):
    # 正式构造拒绝把跨区落脚点配置到动态箱子的已开终点。
    def test_portal_cannot_land_inside_cargo(self) -> None:
        # 默认会话公开提供已冻结定义。
        session = new_session()
        # 货门来自正式地图，其他通路保持不变。
        room = session.level.room("A")
        # 只改变目标落脚，模拟错误JSON或直接配置调用。
        portals = tuple(replace(portal, target_position=(2, 2)) if portal.id == "a_cargo" else portal
                        # 其余合法连接作为对照。
                        for portal in room.portals)
        # 生成新房间，不穿透冻结定义私有字段。
        replacement = replace(room, portals=portals)
        # 保留六区和其他正式配置。
        rooms = tuple(replacement if item.id == "A" else item for item in session.level.rooms)
        # 错误配置必须在构造边界拒绝，不能等玩家跨门才陷入箱子。
        with self.assertRaises(ValueError):
            # 会话公开构造与包数据加载复用同一校验。
            type(session)(replace(session.level, rooms=rooms), session.rules)

    # 同一时间曲必须双向切换，错误音区和未完成输入不能改变世界。
    def test_shared_time_song_and_optional_lullaby(self) -> None:
        # 新局从默认入口建立。
        session = new_session()
        # 序章玩家拔剑进入成年探索。
        interact_with(session, "sword")
        # 第一次完整时间曲切夜。
        play(session, "time_shift")
        # 真实相位应与输入效果一致。
        self.assertFalse(session.snapshot().is_day)
        # 相同曲再次演奏回白天。
        play(session, "time_shift")
        # 不需要第二首白天曲。
        self.assertTrue(session.snapshot().is_day)
        # 少一个音只有反馈，不触发时间变化。
        melody = next(item for item in session.rules.melodies if item.id == "time_shift")
        # 未完成输入仍提交正式校验边界。
        session.play_keyboard(melody.notes[:-1])
        # 时间状态应完整保留。
        self.assertTrue(session.snapshot().is_day)
        # 摇篮彩蛋不知道也不影响主线，不限制拥有谱才能施法。
        play(session, "egg_lullaby")
        # 彩蛋不能冒充天亮、年龄变化或胜利。
        self.assertTrue(session.snapshot().is_day)
        # 必须有真实可见回馈事件。
        self.assertEqual(session.snapshot().events[-1].kind, "egg_lullaby")
        # 高音写错不应再次命中摇篮曲。
        wrong = ((7, 0), (2, 0), (6, 0)) * 2
        # 提交完整错八度序列。
        session.play_keyboard(wrong)
        # 当前局仍是未通关的成年探索。
        self.assertFalse(session.snapshot().is_won)

    # 布尔、非法事件形状与越界输入应明确拒绝。
    def test_note_boundaries(self) -> None:
        # 非法输入分别覆盖类型、音符和八度。
        for notes in ([(1, 0)], ((True, 0),), ((1, False),), ((0, 0),), ((8, 0),), ((1, 2),), ((1,),), ((1, 0),) * 13):
            # 边界错误不能当普通错音吞掉。
            with self.assertRaises(ValueError):
                # 使用正式最大12音约束。
                validate_notes(notes, 12)

    # 开箱收录、完整失败恢复和事件游标应作为一份业务状态工作。
    def test_checkpoint_retry_and_event_sequence(self) -> None:
        # 经真实默认路径到F夜间安全检查点。
        session = reach_night_checkpoint()
        # 保存测试预期是公开不可变快照。
        checkpoint = session.snapshot()
        # 两个曲谱均真实领取并跨年龄保留。
        self.assertEqual(set(checkpoint.collected_scores), {"time_shift", "egg_lullaby"})
        # 成年推开的货运门在少年仍保持开放。
        self.assertTrue(checkpoint.box_open)
        # 同一曲从夜晚切白天，演奏本身不等于胜利。
        play(session, "time_shift")
        # 站在F等待鸡真实捕获。
        advance(session, 30.0)
        # 捕获应进入失败阶段。
        self.assertEqual(session.snapshot().phase, "failed")
        # 保存失败后最大事件游标。
        failed_sequence = session.snapshot().events[-1].sequence
        # 只通过公开重试恢复完整状态。
        self.assertTrue(session.retry())
        # 恢复后是实际夜间检查点。
        restored = session.snapshot()
        # 位置不能凭故事把玩家移动到另一个门前。
        self.assertEqual((restored.region, restored.pos), (checkpoint.region, checkpoint.pos))
        # 两时代鸡群、箱子、谱箱与收录全部恢复。
        self.assertEqual(restored.chicken_state, checkpoint.chicken_state)
        # 当前相位来自检查点而非失败时白天。
        self.assertFalse(restored.is_day)
        # 已开箱记录必须和收录集合一致。
        self.assertEqual(restored.opened_chests, checkpoint.opened_chests)
        # 已取得谱在重试后仍完整保留。
        self.assertEqual(restored.collected_scores, checkpoint.collected_scores)
        # 事件游标不能回滚导致声音漏播。
        self.assertGreater(restored.events[-1].sequence, failed_sequence)
        # 完整重开与重试明显不同。
        session.restart()
        # 新局不保留箱和谱收集。
        self.assertFalse(session.snapshot().box_open)
        # 彩蛋谱也重置未领取。
        self.assertEqual(session.snapshot().collected_scores, ())
        # 本会话事件序号仍递增。
        self.assertGreater(session.snapshot().events[-1].sequence, restored.events[-1].sequence)

    # 从F原路补拿可选谱，再次安全入场必须刷新完整检查点。
    def test_return_for_optional_score_refreshes_checkpoint(self) -> None:
        # 主线允许初次不打开彩蛋箱。
        session = reach_night_checkpoint(include_lullaby=False)
        # 合法夜间沿原洞返回E。
        cross(session, "f_e")
        # 同一夜闸允许原路退回D。
        cross(session, "e_d")
        # B普通门提供实际补拿路线。
        cross(session, "d_b")
        # 长死胡同中真正打开第二谱箱。
        interact_with(session, "score_lullaby")
        # 沿真实主线重新进入夜间F。
        cross(session, "b_gate")
        # 夜闸按当前夜晚条件通行。
        cross(session, "d_e")
        # 少年通过同一竹结排水口。
        cross(session, "drain_tracks")
        # 记录已刷新检查点的实际业务状态。
        checkpoint = session.snapshot()
        # 新取得谱和谱箱均进入新快照。
        self.assertEqual(set(checkpoint.collected_scores), {"time_shift", "egg_lullaby"})
        # 切昼留在鸡领地内等真实捕获。
        play(session, "time_shift")
        # 推进到实际失败而不注入测试捕获。
        advance(session, 30.0)
        # 重试只能在真实失败后调用。
        self.assertTrue(session.retry())
        # 完整恢复不能退回补拿前的旧谱册。
        restored = session.snapshot()
        # 当前落脚点仍为F实际入口。
        self.assertEqual((restored.region, restored.pos, restored.is_day), ("F", (0, 6), False))
        # 鸡群、货路和两个宝箱状态全部一致。
        self.assertEqual(restored.chicken_state, checkpoint.chicken_state)
        # 共享货箱状态随刷新检查点保存。
        self.assertEqual(restored.box_open, checkpoint.box_open)
        # 新收录不会被旧快照覆盖。
        self.assertEqual(restored.collected_scores, checkpoint.collected_scores)
        # 收录和箱盖状态保持原子一致。
        self.assertEqual(restored.opened_chests, checkpoint.opened_chests)

    # 真正跨门、出口过场与玩家领奖必须分开。
    def test_exit_reveal_and_manual_reward(self) -> None:
        # 走到合法的少年夜间F状态。
        session = reach_night_checkpoint()
        # 先夜间走到出口门前，给真实演奏和逃跑空间。
        portal = next(item for item in session.level.room("F").portals if item.id == "f_g")
        # 夜间闭门不删除门前地板。
        walk_to(session, (portal.position[0] - 1, portal.position[1]))
        # 相同时间曲切白天，启动警告但尚未通关。
        play(session, "time_shift")
        # 演奏完成必须仍留在F。
        self.assertFalse(session.snapshot().is_won)
        # 真正从出口边界跨入G。
        cross(session, "f_g")
        # 越界记录胜利并开始有限过场。
        self.assertEqual(session.snapshot().phase, "exit_reveal")
        # 奖励不能在过场开始时自动领取。
        self.assertFalse(session.snapshot().reward_claimed)
        # 暂停应冻结运镜和动作进度。
        session.set_paused(True)
        # 保存实际进度用于独立比较。
        paused_progress = session.snapshot().cutscene_progress
        # 真实更新时间不能推进暂停模型。
        advance(session, 2.0)
        # 暂停语义是业务冻结。
        self.assertEqual(session.snapshot().cutscene_progress, paused_progress)
        # 解除暂停继续正式过场。
        session.set_paused(False)
        # 跳过和自然结束都由会话进入同一领奖状态。
        session.skip_cutscene()
        # 跳过不能自动开宝箱。
        self.assertEqual(session.snapshot().phase, "reward")
        # 领奖前仍然保持未领取。
        self.assertFalse(session.snapshot().reward_claimed)
        # 玩家自己走到箱旁并交互。
        interact_with(session, "reward_chest")
        # 两件固定奖励由真实一次领取状态表示。
        self.assertTrue(session.snapshot().reward_claimed)
        # 重复交互不产生第二条领奖事件。
        count = sum(event.kind == "reward_claimed" for event in session.snapshot().events)
        # 同一位置再次交互。
        session.interact()
        # 重复操作不能重复发奖。
        self.assertEqual(sum(event.kind == "reward_claimed" for event in session.snapshot().events), count)

    # 不打开彩蛋箱也应能完成原创主线。
    def test_main_route_without_optional_score(self) -> None:
        # 只实际领取唯一时间曲。
        session = reach_night_checkpoint(include_lullaby=False)
        # 彩蛋不能变成必收条件。
        self.assertEqual(session.snapshot().collected_scores, ("time_shift",))
        # 同曲切白天并通过真实出口。
        play(session, "time_shift")
        # 出口条件由真实跨门满足。
        cross(session, "f_g")
        # 没有彩蛋谱的玩家仍应胜利。
        self.assertTrue(session.snapshot().is_won)
        # 自然完成过场而非仅跳过分支。
        advance(session, session.rules.exit_seconds + 0.01)
        # 过场结束仍须等待手动领奖。
        self.assertEqual(session.snapshot().phase, "reward")
        # 不自动给未交互的奖励。
        self.assertFalse(session.snapshot().reward_claimed)

    # 门槛上切白天不能夹人，离开后又真实关闭。
    def test_occupied_night_gate(self) -> None:
        # 到达完整夜间状态。
        session = reach_night_checkpoint()
        # 从F原路退回E。
        cross(session, "f_e")
        # 走到E侧同一夜闸门槛。
        portal = next(item for item in session.level.room("E").portals if item.id == "e_d")
        # 夜晚允许站门槛。
        walk_to(session, portal.position)
        # 当前占用门槛时切成白天。
        play(session, "time_shift")
        # 地板与位置不能被偷偷替换。
        self.assertEqual(session.snapshot().pos, portal.position)
        # 占用者仍能沿原门跨出，不能被关在门里。
        self.assertTrue(session.move(portal.direction))
        # 真实移动完成。
        advance(session, session.rules.movement_seconds + 0.01)
        # 出门落在D而不被弹回E。
        self.assertEqual(session.snapshot().region, "D")
        # 向内离开D门槛后延迟关闭应解除。
        self.assertTrue(session.move("left"))
        # 等待落脚完成。
        advance(session, session.rules.movement_seconds + 0.01)
        # 白天再次走回闭门格应拒绝。
        self.assertFalse(session.move("right"))

    # 成年开通后的同一货门在四种年龄昼夜组合均可往返。
    def test_cargo_four_states(self) -> None:
        # 完整路线已把箱子开通并变回孩童。
        session = reach_night_checkpoint()
        # 未来鸡曾进入白天警告，之后真实切夜。
        cross(session, "f_e")
        # 夜间原路回剑台，不利用测试状态跳转。
        cross(session, "e_d")
        # 经普通B门。
        cross(session, "d_b")
        # 孩童窄门回A。
        cross(session, "b_child")
        # 每个年龄均验证白天与夜晚的双向货门。
        for age_index in range(2):
            # 同一年龄检查两个相位。
            for _ in range(2):
                # 开通后A到C应真实允许。
                cross(session, "a_cargo")
                # C到A同样是双向。
                cross(session, "c_a")
                # 时间曲切换当前相位，开通状态不能重置。
                play(session, "time_shift")
                # 共享状态应始终开放。
                self.assertTrue(session.snapshot().box_open)
            # 第一轮结束后通过真实剑台切成年。
            if age_index == 0:
                # 不直接写Timeline年龄。
                interact_with(session, "sword")
        # 当前成年时回少年，年龄变化保留相位。
        interact_with(session, "sword")
        # 时代和通道必须仍一致。
        self.assertEqual(session.snapshot().age, "child")

    # 鸡群的位置、警戒模式与计时均按时代独立，不只检查容器数量。
    def test_chicken_eras_keep_independent_state(self) -> None:
        # 从默认入口经实际成年路线开通货门。
        session = new_session()
        # 剑台切成年保留另一时代初始鸡群。
        interact_with(session, "sword")
        # 滑落连接由真实动画完成。
        cross(session, "a_slide")
        # 普通货道两龄均可进入。
        cross(session, "b_cargo")
        # 箱子只通过成年正向施力打开。
        interact_with(session, "cargo_box")
        # 等待箱子进入凹位后再行走。
        advance(session, session.rules.box_seconds + 0.01)
        # 保存两个时代逐字段初始状态。
        initial = dict(session.snapshot().chicken_state)
        # 成年沿普通路线抵达夜闸。
        cross(session, "c_b")
        # 从B进入D不依赖彩蛋或少年能力。
        cross(session, "b_gate")
        # 在完整安全地面切夜才通过闸门。
        walk_to(session, (17, 6))
        # 唯一时间曲打开同一夜闸。
        play(session, "time_shift")
        # 正式跨门进入E。
        cross(session, "d_e")
        # 同一旋律切昼，允许成年鸡在领地内警告。
        play(session, "time_shift")
        # 实际进入领地而非直接修改鸡状态。
        walk_to(session, (6, 9))
        # 留出少量计时使警告值真实变化。
        advance(session, 0.2)
        # 读取当前两个独立时代快照。
        changed = dict(session.snapshot().chicken_state)
        # 成年鸡状态确实有变化，避免测试没有施加有效刺激。
        self.assertNotEqual(changed["adult"], initial["adult"])
        # 少年鸡位置、模式和计时全部保持原值。
        self.assertEqual(changed["child"], initial["child"])
        # 主动切夜停止危险并开始真实归巢。
        play(session, "time_shift")
        # 沿可恢复的实际回程回剑台。
        cross(session, "e_d")
        # 普通门回B。
        cross(session, "d_b")
        # 已开的货道回C。
        cross(session, "b_cargo")
        # 已开货门允许成年回A。
        cross(session, "c_a")
        # 保持白天检查未激活时代的计时冻结。
        play(session, "time_shift")
        # 切年龄前保存成年时代完整鸡群。
        adult_before = dict(session.snapshot().chicken_state)["adult"]
        # 正式插剑切少年，不写私有时代字段。
        interact_with(session, "sword")
        # 当前少年世界更新不能继续成年鸡群计时。
        advance(session, 1.0)
        # 最后再次逐字段读取两时代。
        final = dict(session.snapshot().chicken_state)
        # 少年状态没有继承成年归巢或警戒。
        self.assertEqual(final["child"], initial["child"])
        # 成年状态在未激活时代保持冻结。
        self.assertEqual(final["adult"], adult_before)

    # 暂停与非法时间增量必须保留模型完整性。
    def test_pause_and_invalid_time(self) -> None:
        # 默认会话的状态由公开快照读取。
        session = new_session()
        # 边界不得用零回退掩盖非法时间。
        for seconds in (-1.0, float("nan"), float("inf"), True, 10 ** 400):
            # 每种无效值必须明确失败。
            with self.assertRaises(ValueError):
                # 调用正式更新时间边界。
                session.update(seconds)
        # 初始探索由玩家交互开始。
        interact_with(session, "sword")
        # 主动暂停冻结位置和鸡群状态。
        session.set_paused(True)
        # 保存完整当前查询值。
        before = session.snapshot()
        # 暂停世界仍可收到显示循环的更新。
        advance(session, 2.0)
        # 鸡群计时和位置不得继续。
        self.assertEqual(session.snapshot().chicken_state, before.chicken_state)
        # 暂停不能提交乐器时间效果。
        play(session, "time_shift")
        # 世界相位仍保留。
        self.assertEqual(session.snapshot().is_day, before.is_day)
