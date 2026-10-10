# 正式输入回归使用真实pygame事件，不需要打开窗口。
import pygame
# 单一测试类沿用标准库回归工具。
import unittest
# 声音替身只记录调用，避免测试依赖真实设备。
from unittest.mock import Mock
# 被测控制器只通过公开模型能力操作。
from time_maze.app.input_controller import InputController
# 每个测试使用独立默认会话。
from support.tests.journey import new_session, interact_with, advance, cross

# 覆盖用户输入重复、失焦、面板隔离与前缀边界。
class TestInput(unittest.TestCase):
    # 实际开箱、查谱再退出后应能立即沿死胡同回程。
    def test_escape_closes_score_panel_without_pausing(self) -> None:
        # 当前会话已真实拔剑，跨滑落口进入B。
        cross(self.session, "a_slide")
        # 首次开箱从玩家邻近交互取得正式曲谱。
        interact_with(self.session, "score_time")
        # 同步探索阶段，后续事件按实际应用顺序消费。
        self.controller.advance(0.0, self.session)
        # 查阅已领取曲谱。
        self.press(pygame.K_k)
        # 输入一个未完成音符，退出必须一起清掉。
        self.press(pygame.K_6)
        # 保存箱旁真实格，回程应发生位置变化。
        position = self.session.snapshot().pos
        # Esc首次只关闭面板，不假定玩家想暂停地图。
        self.controller.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, repeat=False), self.session, self.audio)
        # 模拟缺repeat标记的重复事件，不能在同一次长按中转为暂停。
        self.controller.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, repeat=False), self.session, self.audio)
        # 面板与旧音符均解除占用。
        self.assertFalse(self.controller.keyboard_snapshot().is_open)
        # 未提交输入不会带到下一次查谱。
        self.assertEqual(self.controller.keyboard_snapshot().notes, ())
        # 关闭面板不应冻结世界。
        self.assertFalse(self.session.snapshot().is_paused)
        # Esc释放后才允许下一次明确控制动作。
        self.controller.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_ESCAPE, mod=0), self.session, self.audio)
        # 箱旁真实回程向左，按住方向与正常应用行为一致。
        self.controller.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT, mod=0, repeat=False), self.session, self.audio)
        # 每帧输入推进应提交实际移动。
        self.controller.advance(0.2, self.session)
        # 移动插值由正式模型完成。
        advance(self.session, 0.2)
        # 离开箱旁，不能只检查面板布尔值。
        self.assertEqual(self.session.snapshot().pos, (position[0] - 1, position[1]))
        # 松开移动键不会留下持续移动。
        self.controller.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_LEFT, mod=0), self.session, self.audio)
        # 返回地图后再次Esc仍提供明确暂停。
        self.press(pygame.K_ESCAPE)
        # 地图暂停功能继续有效。
        self.assertTrue(self.session.snapshot().is_paused)
        # 再次Esc仍可恢复当前局。
        self.press(pygame.K_ESCAPE)
        # 当前箱和已收录曲谱无需重开即可继续。
        self.assertFalse(self.session.snapshot().is_paused)

    # 每次建立独立输入、世界和声音替身。
    def setUp(self) -> None:
        # 新会话不继承另一测试的状态。
        self.session = new_session()
        # 拔剑后允许真实探索和演奏。
        interact_with(self.session, "sword")
        # 容量从正式规则传入。
        self.controller = InputController(self.session.rules.max_notes)
        # 音频播放不决定匹配结果。
        self.audio = Mock()
        # 同步当前正式阶段，后续事件不与初次阶段检测混淆。
        self.controller.advance(0.01, self.session)

    # 首次按下与释放组成一个完整物理操作。
    def press(self, key: int, modifiers: int = 0) -> None:
        # 控制器接收真实pygame按下事件。
        self.controller.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=modifiers, repeat=False), self.session, self.audio)
        # 释放完成后才允许同键再次输入。
        self.controller.handle_event(pygame.event.Event(pygame.KEYUP, key=key, mod=modifiers), self.session, self.audio)

    # 自动重复不能开关面板或重复收音。
    def test_repeat_filter_and_single_note(self) -> None:
        # 第一次K应打开面板。
        self.controller.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_k, mod=0, repeat=False), self.session, self.audio)
        # 系统随后发送K自动重复。
        self.controller.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_k, mod=0, repeat=True), self.session, self.audio)
        # 面板不能被自动重复关闭。
        self.assertTrue(self.controller.keyboard_snapshot().is_open)
        # 释放K结束该次操作。
        self.controller.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_k, mod=0), self.session, self.audio)
        # 组合音7只生成一条音符事件。
        self.controller.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_7, mod=0, repeat=False), self.session, self.audio)
        # 重复按下7不能生成第二个音。
        self.controller.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_7, mod=0, repeat=True), self.session, self.audio)
        # 本次前缀是单音，不是三键和弦。
        self.assertEqual(self.controller.keyboard_snapshot().notes, ((7, 0),))
        # 声音只播放同一个单音一次。
        self.audio.play_note.assert_called_once_with(7, 0)

    # 乐器界面不能移动玩家，关闭必须清前缀。
    def test_panel_isolation_and_limit(self) -> None:
        # 打开面板后输入归乐器独占。
        self.press(pygame.K_k)
        # 保存真实玩家初始位置。
        position = self.session.snapshot().pos
        # 高八度音仍是一条离散事件。
        self.press(pygame.K_2, pygame.KMOD_SHIFT)
        # 向右操作在面板里不转换为移动。
        self.press(pygame.K_RIGHT)
        # 正式输入控制更新依然不得移动。
        self.controller.advance(0.2, self.session)
        # 位置由公开快照比较。
        self.assertEqual(self.session.snapshot().pos, position)
        # 前缀的八度必须保留。
        self.assertEqual(self.controller.keyboard_snapshot().notes, ((2, 1),))
        # 多次输入超过上限时不无限增长。
        for _ in range(20):
            # 每次按下都有真实释放。
            self.press(pygame.K_1)
        # 真实容量来自正式配置。
        self.assertEqual(len(self.controller.keyboard_snapshot().notes), self.session.rules.max_notes)
        # 关闭面板清除未提交前缀。
        self.press(pygame.K_k)
        # 输入快照不能保留上轮音符。
        self.assertEqual(self.controller.keyboard_snapshot().notes, ())

    # 重复失焦应冻结并保留失焦之前的主动暂停状态。
    def test_duplicate_focus_and_pause(self) -> None:
        # 演奏中的前缀必须在失焦时清理。
        self.press(pygame.K_k)
        # 一个音尚未构成完整时间曲。
        self.press(pygame.K_6)
        # 第一次焦点丢失触发真实暂停。
        self.controller.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST), self.session, self.audio)
        # 系统重复发送丢焦不应覆盖原暂停标记。
        self.controller.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST), self.session, self.audio)
        # 模型已暂停。
        self.assertTrue(self.session.snapshot().is_paused)
        # 旧音符不能留到焦点恢复后。
        self.assertEqual(self.controller.keyboard_snapshot().notes, ())
        # 重新获得焦点恢复原来的未暂停状态。
        self.controller.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED), self.session, self.audio)
        # 不能因重复失焦变成永久暂停。
        self.assertFalse(self.session.snapshot().is_paused)
        # 用户主动暂停先于下一次失焦。
        self.press(pygame.K_ESCAPE)
        # 再丢失焦点。
        self.controller.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST), self.session, self.audio)
        # 恢复焦点不取消用户主动暂停。
        self.controller.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED), self.session, self.audio)
        # 模型仍保持主动暂停。
        self.assertTrue(self.session.snapshot().is_paused)

    # 已有焦点时的迟来获得焦点事件不能解除用户主动暂停。
    def test_duplicate_focus_gain_preserves_pause(self) -> None:
        # Esc主动暂停是明确玩家状态。
        self.press(pygame.K_ESCAPE)
        # 模型暂停应立刻生效。
        self.assertTrue(self.session.snapshot().is_paused)
        # 没有先发生失焦的GAINED属于重复或迟来事件。
        self.controller.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED), self.session, self.audio)
        # 再次GAINED也不能取消主动暂停。
        self.controller.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED), self.session, self.audio)
        # 原本焦点未丢失，主动暂停仍应保留。
        self.assertTrue(self.session.snapshot().is_paused)
