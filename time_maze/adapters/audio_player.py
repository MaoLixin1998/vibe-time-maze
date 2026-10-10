# 标准数组用于合成PCM缓冲，不依赖外部音频素材。
from array import array
# 正弦与包络计算生成基础笛子单音。
import math
# 设备初始化只在显式start中发生。
import pygame
# 事件快照提供单调序号，避免恢复后漏播或重复。
from time_maze.model.game_event import GameEvent

# 基础音区从C5开始，七音只输出单条音高。
BASE_FREQUENCY_HZ = 523.2511306
# 自然大调七音对应半音距离。
SCALE_SEMITONES = (0, 2, 4, 5, 7, 9, 11)
# 采样率与设备初始化一致，单位为每秒样本数。
SAMPLE_RATE_HZ = 44100
# 单音有足够听辨长度，不决定输入节奏要求。
NOTE_SECONDS = 0.24
# 总幅度控制为较轻的提示声。
NOTE_VOLUME = 0.16


# 音符与八度在合成和播放边界共用验证，不接受bool或越界值。
def validate_note(note_id: int, octave: int) -> None:
    # bool不能被当作音符编号或八度值。
    if type(note_id) is not int or type(octave) is not int:
        # 调用者错误不静默吞掉。
        raise ValueError("note and octave must be integers")
    # 当前只提供七音、基础及高八度。
    if not 1 <= note_id <= 7 or octave not in (0, 1):
        # 不用默认音高掩盖非法请求。
        raise ValueError("note must be 1..7 and octave must be 0 or 1")

# 合成柔和笛音，二次谐波很轻，不输出同时多个音高的和弦。
def synthesize_note_pcm(note_id: int, octave: int) -> bytes:
    # 纯合成接口先验证七音与音区，不读取音频设备。
    validate_note(note_id, octave)
    # 基础频率按十二平均律和完整八度换算。
    frequency_hz = BASE_FREQUENCY_HZ * 2 ** (SCALE_SEMITONES[note_id - 1] / 12 + octave)
    # 有限长度避免后台持续播放。
    sample_count = int(SAMPLE_RATE_HZ * NOTE_SECONDS)
    # 16位有符号数组作为双声道PCM载体。
    samples = array("h")
    # 所有样本在启动时计算，播放时不逐帧合成。
    for sample_index in range(sample_count):
        # 将样本位置换算为秒。
        time_seconds = sample_index / SAMPLE_RATE_HZ
        # 轻缓起音和收音避免明显爆音。
        envelope = min(1.0, time_seconds / 0.015, (sample_count - 1 - sample_index) / (SAMPLE_RATE_HZ * 0.05))
        # 单一基频配低比例泛音形成基础笛声。
        wave = math.sin(math.tau * frequency_hz * time_seconds)
        # 泛音属于同一个单音的音色，不是独立和弦音符。
        wave += 0.10 * math.sin(math.tau * frequency_hz * 2 * time_seconds)
        # 正确量化至16位范围，包络与低幅度防止溢出。
        sample = int(32767 * NOTE_VOLUME * envelope * wave / 1.10)
        # 左右通道写相同样本，不依赖空间音频。
        samples.extend((sample, sample))
    # pygame Sound缓存保存自己的PCM，临时数组可释放。
    return samples.tobytes()


# 音频适配器持有启动缓存及事件游标，设备失败时保留明确静音原因。
class AudioPlayer:
    # 构造不触碰设备，应用负责显式启动。
    def __init__(self, is_silent: bool = False) -> None:
        # 静音是用户参数，不伪装成设备正常播放。
        self._is_silent = is_silent
        # 未启动时没有声音资源。
        self._sounds: dict[tuple[int, int], pygame.mixer.Sound] = {}
        # 音符与效果使用不同通道避免互相误计为识别。
        self._note_channel: pygame.mixer.Channel | None = None
        # 效果通道由本适配器持有。
        self._effect_channel: pygame.mixer.Channel | None = None
        # 空字符串表示没有启动故障。
        self._unavailable_reason = "Silent mode requested" if is_silent else ""
        # 是否完成启动用于幂等控制。
        self._has_started = False
        # 只有本适配器实际启动的设备才由它关闭。
        self._owns_mixer = False
        # 序号只向前推进，不受检查点恢复影响。
        self._event_sequence = 0

    # 显式初始化设备并缓存基础和高八度共十四个单音。
    def start(self) -> None:
        # 重复调用不重新初始化缓存或设备。
        if self._has_started:
            # 保留已有生命周期状态。
            return
        # 标记已经尝试启动，失败后也不逐帧重试设备。
        self._has_started = True
        # 用户静音时完全不访问声音设备。
        if self._is_silent:
            # 输入和世界仍可完整运行。
            return
        # 最了解音频失败的边界保留pygame原因。
        try:
            # 双声道16位PCM与合成数组一致。
            previous_format = pygame.mixer.get_init()
            # 新设备属于本适配器；已有兼容设备只借用通道。
            if previous_format is None:
                # PCM格式与缓存完全一致。
                pygame.mixer.init(frequency=SAMPLE_RATE_HZ, size=-16, channels=2, buffer=512)
                # 成功初始化后再声明设备所有权。
                self._owns_mixer = True
            # 已有不兼容设备不能播放错误采样格式。
            elif previous_format != (SAMPLE_RATE_HZ, -16, 2):
                # 保留明确静音原因，不关闭其他调用方设备。
                self._unavailable_reason = "Audio unavailable: an incompatible mixer is already active"
                # 不改变其他设备的设置或创建错误缓存。
                return
            # 提示单音和结果效果各使用一个明确通道。
            pygame.mixer.set_num_channels(2)
            # 单音通道播放最新输入，组合不会拆成多个音。
            self._note_channel = pygame.mixer.Channel(0)
            # 结果通道只消费稳定业务事件。
            self._effect_channel = pygame.mixer.Channel(1)
            # 两个音区各缓存七个音。
            for octave in (0, 1):
                # note_id采用正式1到7映射。
                for note_id in range(1, 8):
                    # 合成一次后包装成可重复播放的Sound。
                    self._sounds[(note_id, octave)] = pygame.mixer.Sound(
                        # PCM只来自程序生成的确定性单音。
                        buffer=synthesize_note_pcm(note_id, octave))
        # 无可用设备是可见静音降级，不能改变业务判定。
        except pygame.error as error:
            # 保留原始原因供HUD和终端明确显示。
            self._unavailable_reason = f"Audio unavailable: {error}"
            # 清理可能已部分完成的初始化。
            self.close()

    # 合法输入事件播放一次，错误音符在适配边界明确拒绝。
    def play_note(self, note_id: int, octave: int) -> None:
        # 与程序合成共享公开离散输入的验证规则。
        validate_note(note_id, octave)
        # 静音或设备降级时输入判定仍继续。
        if self._note_channel is None:
            # 不报告实际播放成功。
            return
        # 一个请求对应一个缓存Sound，绝不拆分组合键。
        self._note_channel.play(self._sounds[(note_id, octave)])

    # 只消费游标之后的结果事件，重试不重新播放历史声音。
    def consume_events(self, events: tuple[GameEvent, ...]) -> None:
        # 事件音只有简短反馈，不能替代主线输入。
        effect_notes = {"chicken_warning": (2, 1), "chicken_call": (3, 1),
                        "score_collected": (5, 1), "box_opened": (1, 1),
                        "egg_lullaby": (7, 0), "won": (1, 1), "failed": (2, 0)}
        # 模型事件按序号有界保留。
        for event in events:
            # 已消费事件不会因恢复再次播放。
            if event.sequence <= self._event_sequence:
                # 继续查看可能的新事件。
                continue
            # 即使静音也推进游标，恢复设备不会补播历史。
            self._event_sequence = event.sequence
            # 只对明确映射的结果给声音反馈。
            if self._effect_channel is not None and event.kind in effect_notes:
                # 曲谱匹配已由模型完成，声音仅作结果提示。
                self._effect_channel.play(self._sounds[effect_notes[event.kind]])

    # HUD只读查询当前静音或设备故障原因。
    @property
    def unavailable_reason(self) -> str:
        # 返回稳定文本，不修改或探测设备。
        return self._unavailable_reason

    # 应用退出与部分初始化失败都使用可重复清理。
    def close(self) -> None:
        # 仅停止本适配器持有的通道，不清理未拥有的音频状态。
        if self._note_channel is not None:
            # 不让退出后留下持续单音。
            self._note_channel.stop()
        # 效果提示同样停止。
        if self._effect_channel is not None:
            # 只停止自己的效果通道。
            self._effect_channel.stop()
        # 只有实际初始化过的设备由本对象关闭。
        if self._owns_mixer:
            # 明确释放声音设备。
            pygame.mixer.quit()
        # 重复close不再次关闭设备。
        self._owns_mixer = False
        # 释放缓存引用，避免持有已经退出的Sound。
        self._sounds.clear()
        # 通道不能在设备结束后继续使用。
        self._note_channel = None
        # 同样清除效果通道。
        self._effect_channel = None
