# 路径参数只转交显式测试截图位置。
from pathlib import Path
# 工厂只读取正式包数据，不自动发现本机制作素材。
from time_maze.adapters.content_loader import load_content
# 会话只组合纯规则与状态。
from time_maze.model.game_session import GameSession
# 应用设备启动由run负责，不在工厂导入时发生。
from time_maze.app.application import Application

# 用已校验内容创建一局及其应用依赖，调用者负责run与退出。
def create_game(is_silent: bool = False, max_frames: int | None = None,
                capture_path: Path | None = None) -> Application:
    # 同一份正式地图与曲谱数据同时供规则和展示。
    level, rules, text = load_content()
    # 世界状态每次工厂调用都独立创建。
    session = GameSession(level, rules)
    # 入口参数不侵入世界业务判断。
    return Application(session, is_silent, max_frames, capture_path, text)
