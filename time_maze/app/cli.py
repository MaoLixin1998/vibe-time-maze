# 参数解析不通过shell执行用户文本。
import argparse
# 输出路径使用真实路径对象，不猜测当前工作目录。
from pathlib import Path
# 入口边界将设备与内容失败转换为可读原因。
import sys
# pygame错误保留具体失败信息。
import pygame
# 工厂普通导入没有设备副作用。
from time_maze.app.game_factory import create_game

# 帧数只用于显式测试，非法输入不能变成无限运行。
def positive_frame_count(value: str) -> int:
    # 非整数保留argparse的参数级错误形式。
    try:
        # 只接受标准十进制整数。
        count = int(value)
    # 不隐藏解析失败原因。
    except ValueError as error:
        # 参数错误不需要创建游戏或设备。
        raise argparse.ArgumentTypeError("frames must be a positive integer") from error
    # 零与负数都不是有限测试帧数。
    if count <= 0:
        # 用户可去掉参数进行普通游戏。
        raise argparse.ArgumentTypeError("frames must be a positive integer")
    # 返回通过边界验证的真实参数。
    return count

# 捕获要求显式绝对路径，默认运行不保存媒体。
def absolute_capture_path(value: str) -> Path:
    # 不自动展开私人目录或猜测路径。
    path = Path(value)
    # 相对路径可能写到未预期位置，这里明确拒绝。
    if not path.is_absolute():
        # 错误在启动之前报告。
        raise argparse.ArgumentTypeError("capture path must be absolute")
    # 路径不是图像存在性要求，运行结束时写入。
    return path

# CLI只负责参数、应用创建及最外层可读错误转换。
def main(argv: list[str] | None = None) -> int:
    # 帮助文字是正式游戏入口使用说明。
    parser = argparse.ArgumentParser(description="Vibe Time Maze playable graybox")
    # 静音仍保留所有可见曲谱及世界反馈。
    parser.add_argument("--silent", action="store_true", help="do not initialize the audio device")
    # 普通运行不限帧，测试可明确设定正整数。
    parser.add_argument("--frames", type=positive_frame_count, help="exit after N rendered test frames")
    # 截图只在明确请求时执行，不默认记录玩家画面。
    parser.add_argument("--capture", type=absolute_capture_path, help="save the final test frame to this absolute path")
    # 解析实际参数，不偷偷替换错误值。
    options = parser.parse_args(argv)
    # 输出媒体必须同时是有限测试运行。
    if options.capture is not None and options.frames is None:
        # 由argparse给出一致的启动错误和非零状态。
        parser.error("--capture requires --frames")
    # 内容和设备错误在入口边界转换为人类可读输出。
    try:
        # 工厂只创建当前正式包的本地应用。
        application = create_game(options.silent, options.frames, options.capture)
        # 所有设备初始化及清理在应用run内完成。
        return application.run()
    # 只捕获已预期的外部边界错误，不吞掉未知实现错误。
    except (ValueError, OSError, pygame.error) as error:
        # 明确保留原始原因，不将失败写成成功。
        print(f"Cannot start Vibe Time Maze: {error}", file=sys.stderr)
        # 非零状态让检查工具看到真实失败。
        return 1
