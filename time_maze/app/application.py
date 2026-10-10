# 路径仅用于显式请求的测试截图，不在默认运行中记录媒体。
from pathlib import Path
# 文字映射只提供展示用途，不决定游戏业务规则。
from collections.abc import Mapping
# pygame设备全部由应用生命周期显式管理。
import pygame
# 会话通过公开能力管理所有纯业务状态。
from time_maze.model.game_session import GameSession
# 输入控制器只将事件转换为合法公开操作。
from time_maze.app.input_controller import InputController
# 声音设备失败时静音保留原因。
from time_maze.adapters.audio_player import AudioPlayer
# 基础字体和底图在启动时缓存。
from time_maze.rendering.resource_bundle import ResourceBundle
# 渲染只消费游戏及键盘快照。
from time_maze.rendering.renderer import Renderer, WINDOW_SIZE

# 目标刷新率与最大可消费墙钟时间都是应用时间参数。
TARGET_FRAMES_PER_SECOND = 60
# 长卡顿不无限追赶，模型还会进一步限制子步。
MAX_FRAME_SECONDS = 0.25

# 单一应用循环拥有窗口、输入、声音以及明确的停止清理。
class Application:
    # 构造只保存依赖，设备启动在run中完成。
    def __init__(self, session: GameSession, is_silent: bool = False,
                 max_frames: int | None = None, capture_path: Path | None = None, text: Mapping[str, str] | None = None) -> None:
        # 会话已由应用工厂使用正式数据创建。
        self._session = session
        # 正式文字由工厂显式注入，不由界面自行读取JSON。
        self._text = text
        # 参数非法时在组装边界报错，不默默改为无限运行。
        if max_frames is not None and (type(max_frames) is not int or max_frames <= 0):
            # 测试帧数必须是正整数。
            raise ValueError("max_frames must be a positive integer")
        # 捕获只接受显式绝对路径与有限测试运行。
        if capture_path is not None and (not capture_path.is_absolute() or max_frames is None):
            # 不依赖当前目录猜测媒体输出位置。
            raise ValueError("capture requires an absolute path and --frames")
        # 创建轻量输入对象，不读取设备。
        self._input = InputController(session.rules.max_notes)
        # 音频同样先保存生命周期对象。
        self._audio = AudioPlayer(is_silent)
        # 记录实际帧数限制，空值表示用户普通玩游戏。
        self._max_frames = max_frames
        # 默认完全不捕获或保存画面。
        self._capture_path = capture_path
        # 设备启动之前没有屏幕。
        self._screen: pygame.Surface | None = None
        # Renderer依赖显示格式，启动时才创建。
        self._renderer: Renderer | None = None
        # 应用可以明确停止，不依赖垃圾回收。
        self._is_running = False
        # 关闭状态让清理可重复调用。
        self._is_closed = False

    # 显式启动单循环，任何异常路径都释放已拥有的设备。
    def run(self) -> int:
        # 已关闭实例不能偷偷重新启动设备。
        if self._is_closed:
            # 若要新运行，调用方应创建新应用。
            raise RuntimeError("Application is already closed")
        # 所有设备初始化位于受finally保护的范围内。
        try:
            # 只启动真实用到的显示子系统。
            pygame.display.init()
            # 字体默认资源独立于本机制作素材。
            pygame.font.init()
            # 默认窗口固定足够大的地图与曲谱空间。
            self._screen = pygame.display.set_mode(WINDOW_SIZE)
            # 标题明确当前几何灰盒阶段。
            caption = self._text.get("title_en", "Vibe Time Maze - playable graybox") if self._text is not None else "Vibe Time Maze - playable graybox"
            # 标题来自正式文字，英文标题也能在无中文字体环境使用。
            pygame.display.set_caption(caption)
            # 静态房间资源只在启动阶段一次准备。
            resources = ResourceBundle(self._session.level)
            # 将纯模型只读定义传入展示层。
            self._renderer = Renderer(self._screen, self._session.level, self._session.rules, resources, self._text)
            # 声音设备不可用时降级并继续完整游戏。
            self._audio.start()
            # 终端同样保留真实静音原因。
            if self._audio.unavailable_reason:
                # 不将静音声称为听感通过。
                print(self._audio.unavailable_reason)
            # 该时钟只属于当前应用，不放入模型。
            clock = pygame.time.Clock()
            # 开始明确的事件循环。
            self._is_running = True
            # 帧计数只用于显式测试运行。
            frame_count = 0
            # 渲染和模拟共同运行，不创建第二条后台游戏循环。
            while self._is_running:
                # 将墙钟毫秒换算为有限秒，不无限追赶长卡顿。
                seconds = min(clock.tick(TARGET_FRAMES_PER_SECOND) / 1000.0, MAX_FRAME_SECONDS)
                # 每帧顺序消费pygame事件。
                for event in pygame.event.get():
                    # 关闭窗口是唯一普通退出动作。
                    if event.type == pygame.QUIT:
                        # 本帧剩余输入不会继续执行。
                        self._is_running = False
                        # 退出事件循环消费。
                        break
                    # 输入层处理重复按键、失焦、面板和世界操作。
                    self._input.handle_event(event, self._session, self._audio)
                # 退出后不再更新世界。
                if not self._is_running:
                    # 保留最后完整画面供显式测试截图。
                    break
                # 输入展示计时及持续移动通过公开能力推进。
                self._input.advance(seconds, self._session)
                # 模型自行处理暂停与完整子步，面板不会暂停它。
                self._session.update(seconds)
                # 更新后再次检查失败等输入清理边界，不重复累计时间。
                self._input.advance(0.0, self._session)
                # 独立只读快照传给渲染，不泄露模型内部状态。
                snapshot = self._session.snapshot()
                # 按单调事件序号消费提示音。
                self._audio.consume_events(snapshot.events)
                # Renderer不持有InputController或会话可变对象。
                self._renderer.draw(snapshot, self._input.keyboard_snapshot(),
                                    self._audio.unavailable_reason)
                # 显示完整绘制结果。
                pygame.display.flip()
                # 只在完整绘图后增加帧数。
                frame_count += 1
                # 有限测试运行达到真实帧数后停止。
                if self._max_frames is not None and frame_count >= self._max_frames:
                    # 普通玩家运行没有此限制。
                    self._is_running = False
            # 只有明确测试参数才保存一张画面。
            if self._capture_path is not None and self._screen is not None:
                # 父目录必须已存在，避免默认新建媒体目录。
                if not self._capture_path.parent.is_dir():
                    # 明确输出错误不会伪装成成功捕获。
                    raise ValueError("Capture parent directory does not exist")
                # 输出路径由启动参数明确提供，不扫描制作目录。
                pygame.image.save(self._screen, str(self._capture_path))
            # 零状态仅表示当前运行生命周期正常结束。
            return 0
        # 所有启动、绘图、声音或捕获失败都必须清理设备。
        finally:
            # 不依赖解释器退出释放窗口。
            self.close()

    # 幂等清理，不允许迟到输入重新启动已停止实例。
    def close(self) -> None:
        # 多次关闭不会重复操作已释放设备。
        if self._is_closed:
            # 清理早已完成。
            return
        # 首先停止循环和旧按键。
        self._is_running = False
        # 立即清除所有输入前缀。
        self._input.clear()
        # 声音停止与设备关闭由适配器负责。
        self._audio.close()
        # 字体对象结束后不再继续绘制。
        pygame.font.quit()
        # 明确关闭本应用显示。
        pygame.display.quit()
        # 释放显示面引用。
        self._screen = None
        # 不保留依赖旧字体和窗口的渲染器。
        self._renderer = None
        # 防止run再次打开设备。
        self._is_closed = True
