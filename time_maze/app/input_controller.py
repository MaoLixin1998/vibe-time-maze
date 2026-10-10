# pygame事件在界面边界转换成正式模型公开操作。
import pygame
# 输入快照不暴露控制器的可变集合。
from time_maze.model.keyboard_snapshot import KeyboardSnapshot
# 游戏会话是所有世界状态变更的公开入口。
from time_maze.model.game_session import GameSession
# 音频播放只是单音反馈，不参与曲谱识别。
from time_maze.adapters.audio_player import AudioPlayer

# 数字键与小键盘均代表一条音符事件。
NOTE_KEYS = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3, pygame.K_4: 4,
             pygame.K_5: 5, pygame.K_6: 6, pygame.K_7: 7, pygame.K_KP1: 1,
             pygame.K_KP2: 2, pygame.K_KP3: 3, pygame.K_KP4: 4,
             pygame.K_KP5: 5, pygame.K_KP6: 6, pygame.K_KP7: 7}
# 移动键同向合并，面板打开后不消费为移动。
DIRECTION_KEYS = (("up", (pygame.K_w, pygame.K_UP)), ("down", (pygame.K_s, pygame.K_DOWN)),
                  ("left", (pygame.K_a, pygame.K_LEFT)), ("right", (pygame.K_d, pygame.K_RIGHT)))

# 控制器独占按键、面板和有界前缀；世界状态只通过会话公开能力改变。
class InputController:
    # 构造仅建立输入状态，最大长度来自已经校验的正式规则。
    def __init__(self, max_notes: int) -> None:
        # 拒绝布尔值及非法长度，避免不可预期的前缀容量。
        if type(max_notes) is not int or max_notes <= 0:
            # 配置错误在组装时明确报告。
            raise ValueError("max_notes must be a positive integer")
        # 保存当前真实配置，不使用可变全局状态。
        self._max_notes = max_notes
        # 按键集合用于过滤操作系统自动重复。
        self._pressed: set[int] = set()
        # 前缀只由本控制器修改。
        self._notes: list[tuple[int, int]] = []
        # 默认关闭乐器，玩家先探索世界。
        self._is_open = False
        # 新窗口视为具有输入焦点。
        self._is_focused = True
        # 首次演奏之前无高亮音符。
        self._last_note: tuple[int, int] | None = None
        # 涟漪初值已经超过展示时长。
        self._last_note_seconds = 10.0
        # 本地输入反馈与业务反馈分开。
        self._feedback = ""
        # 失焦恢复时保留用户原本的暂停状态。
        self._was_paused_before_focus_loss = False
        # 用上一帧阶段识别失败等需要清空的边界。
        self._last_phase = ""

    # 清除所有输入，不把旧音符带到暂停、重试或新一局。
    def clear(self, close_panel: bool = True) -> None:
        # 释放按键可避免恢复后继续移动。
        self._pressed.clear()
        # 曲谱必须在同一次面板输入内完整提交。
        self._notes.clear()
        # 旧高亮不应出现在下一轮输入。
        self._last_note = None
        # 重置涟漪时长。
        self._last_note_seconds = 10.0
        # 清除上一轮输入反馈。
        self._feedback = ""
        # 调用者可在清前缀时保留面板。
        if close_panel:
            # 默认关闭面板并返回探索视图。
            self._is_open = False

    # 转换单个事件；重复按键不追加音符或重复执行交互。
    def handle_event(self, event: pygame.event.Event, session: GameSession,
                     audio: AudioPlayer) -> None:
        # 焦点丢失是独立生命周期边界。
        if event.type == pygame.WINDOWFOCUSLOST and self._is_focused:
            # 记录原暂停状态供恢复使用。
            self._was_paused_before_focus_loss = session.snapshot().is_paused
            # 明确冻结模型，不只停止绘图。
            session.set_paused(True)
            # 清除正在按下的键与音符。
            self.clear()
            # HUD会说明失焦冻结。
            self._is_focused = False
            # 本事件没有其他按键含义。
            return
        # 焦点恢复不应取消用户主动暂停。
        if event.type == pygame.WINDOWFOCUSGAINED and not self._is_focused:
            # 恢复记录的暂停状态。
            session.set_paused(self._was_paused_before_focus_loss)
            # 窗口现在可以接收新的按键。
            self._is_focused = True
            # 不从旧按键恢复移动。
            return
        # 释放事件始终移除按键，避免长按状态残留。
        if event.type == pygame.KEYUP:
            # discard允许重复释放同一个键。
            self._pressed.discard(event.key)
            # 释放不触发演奏或交互。
            return
        # 只处理获得焦点后的首次按下。
        if event.type != pygame.KEYDOWN or not self._is_focused or event.key in self._pressed or getattr(event, "repeat", False):
            # 鼠标等事件在本轮灰盒没有业务动作。
            return
        # 记录真实按下，直到KEYUP或状态边界清除。
        self._pressed.add(event.key)
        # 只读快照用于判断当前操作是否适用。
        snapshot = session.snapshot()
        # 面板中Esc先返回地图，避免玩家退出查谱时意外暂停整局。
        if event.key == pygame.K_ESCAPE:
            # 已暂停时仍保留恢复能力，普通演奏状态则只关闭面板。
            if self._is_open and not snapshot.is_paused:
                # 丢弃未提交音符并解除面板对移动输入的占用。
                self.clear()
                # Esc释放前不允许重复事件紧接着暂停地图。
                self._pressed.add(event.key)
                # 关闭查谱不改变世界暂停状态。
                return
            # 清掉所有可能继续触发的按键。
            self.clear()
            # 本次控制键保持按下记录，直到KEYUP才可再次触发。
            self._pressed.add(event.key)
            # 通过模型公开接口切换暂停。
            session.set_paused(not snapshot.is_paused)
            # 暂停操作不再触发其他动作。
            return
        # 完整重开与失败重试使用不同明确按键。
        if event.key == pygame.K_F5:
            # 清除前一局所有输入。
            self.clear()
            # 保留当前控制键，避免没有repeat字段的重复事件重开。
            self._pressed.add(event.key)
            # 完整重开由模型重置业务数据。
            session.restart()
            # 不将F5解释成其他动作。
            return
        # 失败时R恢复完整检查点。
        if event.key == pygame.K_r and snapshot.phase == "failed":
            # 清前缀避免失败前的音符补接。
            self.clear()
            # 当前R仍须等待释放，避免重复恢复尝试。
            self._pressed.add(event.key)
            # 只在真实失败阶段调用retry。
            session.retry()
            # 恢复完成后等待新输入。
            return
        # 暂停或失败时不允许剩余游戏操作。
        if snapshot.is_paused or snapshot.phase == "failed":
            # 恢复和重开已在上面明确处理。
            return
        # Space可跳过正式可跳过过场。
        if event.key == pygame.K_SPACE:
            # 不修改动画内部进度，由会话完成合法结束。
            session.skip_cutscene()
            # 跳过不同时演奏。
            return
        # 过场期间不打开键盘或执行探索动作。
        if snapshot.phase in {"sliding", "pushing", "exit_reveal"}:
            # 动态过程由模型推进。
            return
        # K切换三键面板，关闭时前缀立即清空。
        if event.key == pygame.K_k:
            # 先记录目标开闭状态，clear默认会关闭。
            next_is_open = not self._is_open
            # 每次打开都开始独立输入。
            self.clear()
            # 面板开闭键持续按住时不能再次切换。
            self._pressed.add(event.key)
            # 应用明确的新面板状态。
            self._is_open = next_is_open
            # 防止面板按键同时作世界交互。
            return
        # 面板聚焦时数字、提交与清空都在输入边界处理。
        if self._is_open:
            # 数字仅增加一条单音，不生成和弦。
            if event.key in NOTE_KEYS:
                # 长度上限先检查，不播放未记录的额外音。
                if len(self._notes) >= self._max_notes:
                    # 超限提供可见文字，世界不变化。
                    self._feedback = "Phrase full - Enter to submit or Backspace to clear"
                    # 不追加或播放第十三个音。
                    return
                # Shift选择高八度，不增加物理第四键。
                octave = int(bool(event.mod & pygame.KMOD_SHIFT))
                # 音符数字与八度作为一条事件保存。
                note = (NOTE_KEYS[event.key], octave)
                # 追加至本次面板的有界前缀。
                self._notes.append(note)
                # 最新单音同时驱动三键组合高亮。
                self._last_note = note
                # 涟漪从当前帧开始计时。
                self._last_note_seconds = 0.0
                # 合法新音清除之前超限反馈。
                self._feedback = ""
                # 声音失败不影响输入记录或规则提交。
                audio.play_note(*note)
            # Enter提交整个短句，不要求节奏。
            elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                # 提交不可变值，不把内部列表交给模型。
                session.play_keyboard(tuple(self._notes))
                # 提交后开始新短句，面板继续打开。
                self.clear(close_panel=False)
                # 提交键在释放前不能重复提交空前缀。
                self._pressed.add(event.key)
            # Backspace是明确的完整前缀清空。
            elif event.key == pygame.K_BACKSPACE:
                # 保留面板方便重新弹奏。
                self.clear(close_panel=False)
                # 清空键也保留按下状态直到释放。
                self._pressed.add(event.key)
            # 面板中的移动键不能影响世界。
            return
        # E是所有邻近真实交互的统一动作。
        if event.key == pygame.K_e:
            # 会话负责邻近距离、年龄与物件状态验证。
            session.interact()

    # 每帧推进输入展示计时并尝试保持按键的网格移动。
    def advance(self, seconds: float, session: GameSession) -> None:
        # 涟漪计时不改变曲谱输入或业务时间。
        self._last_note_seconds += seconds
        # 查询阶段而不持有模型内部引用。
        snapshot = session.snapshot()
        # 进入失败或过场要立即清掉前缀与移动键。
        if snapshot.phase != self._last_phase and snapshot.phase in {
            "failed", "sliding", "pushing", "exit_reveal"}:
            # 模型主动改变阶段时输入也遵守边界清理。
            self.clear()
        # 保留本帧阶段用于下一次边界判断。
        self._last_phase = snapshot.phase
        # 面板、暂停及失焦都会禁止玩家移动输入。
        if self._is_open or snapshot.is_paused or not self._is_focused:
            # 模型更新是否继续由Application决定。
            return
        # 只有允许探索的阶段接受移动。
        if snapshot.phase not in {"intro", "exploring", "reward"}:
            # 失败与动画不能被移动打断。
            return
        # 一帧仅选择一个方向，避免斜向移动两格。
        for direction, keys in DIRECTION_KEYS:
            # 任一同义移动键按住即可尝试一次合法移动。
            if any(key in self._pressed for key in keys):
                # 模型在移动插值期间拒绝重复移动。
                session.move(direction)
                # 不在同一帧再尝试其他方向。
                break

    # 返回独立不可变展示值，Renderer不持有控制器。
    def keyboard_snapshot(self) -> KeyboardSnapshot:
        # 复制音符元组，嵌套项本身也不可变。
        return KeyboardSnapshot(self._is_open, tuple(self._notes), self._last_note,
                                self._last_note_seconds, self._is_focused, self._feedback)
