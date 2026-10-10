# PCM验证直接检查样本，不要求测试机器具有声音设备。
from array import array
# 正式回归只使用标准库测试工具。
import unittest
# 声音设备替身记录公开调用，不访问适配器私有字段。
from unittest.mock import Mock, patch
# 被测合成接口和设备生命周期位于同一音频适配职责。
from time_maze.adapters.audio_player import AudioPlayer, synthesize_note_pcm, SAMPLE_RATE_HZ, NOTE_SECONDS
# 结果序号来自正式事件类型，不读取模型内部状态。
from time_maze.model.game_event import GameEvent

# 通过公开PCM及设备调用验证七音、八度、静音和恢复后的事件消费。
class TestAudio(unittest.TestCase):
    # 将双声道PCM转换成独立左声道样本，供音高测量。
    def samples(self, note_id: int, octave: int) -> array:
        # PCM来自被测公开纯函数，不启动设备。
        pcm = synthesize_note_pcm(note_id, octave)
        # h表示16位有符号样本。
        values = array("h")
        # 明确读取完整缓冲，不依赖文件。
        values.frombytes(pcm)
        # 返回左声道，不通过私有缓存获得样本。
        return values[::2]

    # 测量稳定段上升过零间隔，避免起收音包络影响估计。
    def measured_frequency(self, values: array) -> float:
        # 稳定中段使用20到180毫秒。
        first_index = int(SAMPLE_RATE_HZ * 0.02)
        # 上界不落入尾部淡出区。
        last_index = int(SAMPLE_RATE_HZ * 0.18)
        # 相邻负正转变对应每个基频周期。
        crossings = [index for index in range(first_index + 1, last_index)
                     if values[index - 1] <= 0 < values[index]]
        # 该稳定时段应包含足够多完整周期。
        self.assertGreater(len(crossings), 20)
        # 使用首尾过零位置估算Hz，比整数周期计数更准确。
        return (len(crossings) - 1) * SAMPLE_RATE_HZ / (crossings[-1] - crossings[0])

    # 十四个音的PCM格式必须与设备声明一致，首尾归零且不削波。
    def test_fourteen_pcm_buffers(self) -> None:
        # 基础和高八度各有七个合法音。
        for octave in (0, 1):
            # 各音分别审查，不只抽测do。
            for note_id in range(1, 8):
                # 定位失败具体音符和八度。
                with self.subTest(note=note_id, octave=octave):
                    # 每次公开合成得到完整PCM缓冲。
                    pcm = synthesize_note_pcm(note_id, octave)
                    # 16位双声道每帧四字节。
                    self.assertEqual(len(pcm), int(SAMPLE_RATE_HZ * NOTE_SECONDS) * 4)
                    # 解码样本以验证幅度和边界。
                    values = array("h")
                    # 程序缓冲不通过私有对象获得。
                    values.frombytes(pcm)
                    # 左右通道保持一致，不引入空间处理。
                    self.assertEqual(values[::2], values[1::2])
                    # 起点必须归零，避免点击爆音。
                    self.assertEqual(tuple(values[:2]), (0, 0))
                    # 最后一帧同样精确归零。
                    self.assertEqual(tuple(values[-2:]), (0, 0))
                    # 不是整段无声的假资源。
                    self.assertGreater(max(abs(value) for value in values), 100)
                    # PCM幅度不达到16位削波边界。
                    self.assertLess(max(abs(value) for value in values), 32767)

    # 同一个七音序号的高八度应为基础频率的两倍。
    def test_high_octave_frequency(self) -> None:
        # 七种音高分别测量。
        for note_id in range(1, 8):
            # 独立测量基础频率，不能只验证合成公式。
            low_hz = self.measured_frequency(self.samples(note_id, 0))
            # 同样方法测量高八度。
            high_hz = self.measured_frequency(self.samples(note_id, 1))
            # PCM测量允许有限采样点误差。
            self.assertAlmostEqual(high_hz / low_hz, 2.0, delta=0.005)
        # 基础音区确实从C5附近开始。
        self.assertAlmostEqual(self.measured_frequency(self.samples(1, 0)), 523.251, delta=1.0)

    # 合成与播放都明确拒绝非法类型与音区，不偷偷替换音高。
    def test_illegal_notes_and_octaves(self) -> None:
        # 静音适配器同样遵守参数边界。
        player = AudioPlayer(is_silent=True)
        # 包含bool、非整数、越界音符和越界音区。
        invalid = ((True, 0), (1, False), ("1", 0), (1.0, 0), (0, 0), (8, 0), (1, -1), (1, 2))
        # 两个公开入口都必须拒绝相同非法请求。
        for note_id, octave in invalid:
            # 合成不应生成任何缓冲。
            with self.assertRaises(ValueError):
                # 调用公开纯函数验证边界。
                synthesize_note_pcm(note_id, octave)
            # 静音模式不能绕过播放参数验证。
            with self.assertRaises(ValueError):
                # 有效参数在静音时会自然无声返回。
                player.play_note(note_id, octave)
        # 释放从未启动的对象也安全。
        player.close()

    # 静音及重复close不访问未拥有设备。
    def test_silent_and_unstarted_close(self) -> None:
        # 设备初始化替身捕获意外调用。
        with patch("pygame.mixer.init") as initialize, patch("pygame.mixer.quit") as shutdown:
            # 未启动对象不能关闭别处的mixer。
            unstarted = AudioPlayer()
            # 在启动前清理是合法边界。
            unstarted.close()
            # 用户显式静音不创建音频缓存或设备。
            silent = AudioPlayer(is_silent=True)
            # 重复start不会突然打开设备。
            silent.start()
            # 再次启动保持静音。
            silent.start()
            # 合法单音在静音模式仍不访问设备。
            silent.play_note(7, 1)
            # 提供真实静音状态文本。
            self.assertIn("Silent", silent.unavailable_reason)
            # 关闭第一次。
            silent.close()
            # 重复关闭第二次。
            silent.close()
            # 两种对象都未初始化设备。
            initialize.assert_not_called()
            # 两种对象都不能关闭未拥有设备。
            shutdown.assert_not_called()

    # 初始化缓存只发生一次；重试后的较大序号仍正常消费。
    def test_cache_events_and_owned_cleanup(self) -> None:
        # 单音通道与结果通道各记录公开播放调用。
        note_channel, effect_channel = Mock(), Mock()
        # 设备替身保持真实方法结构，不要求GUI或声音硬件。
        with patch("pygame.mixer.get_init", return_value=None), patch("pygame.mixer.init") as initialize, \
             patch("pygame.mixer.set_num_channels"), patch("pygame.mixer.Channel", side_effect=(note_channel, effect_channel)), \
             patch("pygame.mixer.Sound", return_value=Mock()) as sound, patch("pygame.mixer.quit") as shutdown:
            # 普通播放器明确启动一次设备。
            player = AudioPlayer()
            # 缓存建立发生在启动。
            player.start()
            # 再次start不能重复合成或初始化。
            player.start()
            # 一次设备初始化足够。
            initialize.assert_called_once()
            # 基础与高八度共十四条Sound缓存。
            self.assertEqual(sound.call_count, 14)
            # 单一组合只播放一次单音。
            player.play_note(7, 0)
            # 单音通道没有变成三键和弦。
            note_channel.play.assert_called_once()
            # 初始事件只播放一次对应效果。
            player.consume_events((GameEvent(1, "score_collected"),))
            # 重试快照含旧事件及新的重试事件。
            player.consume_events((GameEvent(1, "score_collected"), GameEvent(2, "retried")))
            # 新鸡警告序号应正常消费，旧收谱不能补播。
            player.consume_events((GameEvent(1, "score_collected"), GameEvent(2, "retried"), GameEvent(3, "chicken_warning")))
            # 两个实际声音对应两个新映射事件。
            self.assertEqual(effect_channel.play.call_count, 2)
            # 第一轮关闭释放拥有的设备。
            player.close()
            # 第二轮关闭不能重复退出设备。
            player.close()
            # 明确拥有设备只退出一次。
            shutdown.assert_called_once()

    # 借用兼容已初始化设备时不得关闭其他所有者的设备。
    def test_borrowed_mixer_not_closed(self) -> None:
        # 已有格式与程序合成完全一致。
        with patch("pygame.mixer.get_init", return_value=(SAMPLE_RATE_HZ, -16, 2)), \
             patch("pygame.mixer.init") as initialize, patch("pygame.mixer.set_num_channels"), \
             patch("pygame.mixer.Channel", side_effect=(Mock(), Mock())), patch("pygame.mixer.Sound", return_value=Mock()), \
             patch("pygame.mixer.quit") as shutdown:
            # 适配器借用已有设备。
            player = AudioPlayer()
            # 兼容PCM无需重新启动。
            player.start()
            # 结束只停止本适配器通道。
            player.close()
            # 没有自己的设备初始化。
            initialize.assert_not_called()
            # 未拥有设备不能关闭。
            shutdown.assert_not_called()
