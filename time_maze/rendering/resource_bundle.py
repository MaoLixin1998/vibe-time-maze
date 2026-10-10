# pygame字体与表面资源只在应用显式创建后准备。
import pygame
# 资源构建与正式拓扑组合，不触碰制作目录。
from time_maze.rendering.generated_resources import build_room_surface
# 地图定义本身是只读纯模型值。
from time_maze.model.level_definition import LevelDefinition

# 持有已经准备的字体与中性底图，渲染不逐帧读取磁盘。
class ResourceBundle:
    # 明确在pygame显示与字体子系统启动后创建。
    def __init__(self, level: LevelDefinition) -> None:
        # 默认字体随pygame分发，必要英文信息在干净环境仍可读。
        self._font_path = pygame.font.match_font("pingfangsc,hiraginosansgb,stheitimedium,arialunicode,microsoftyahei,notosanscjk,wenquanyizenhei")
        # 是否可用中文字体只影响额外中文信息显示。
        self.has_cjk_font = self._font_path is not None
        # 常用字号启动时一次缓存。
        self._fonts = {size: pygame.font.Font(self._font_path, size)
                       for size in (16, 18, 20, 24, 30, 38, 48)}
        # 每区只有一份中性底图，角色与昼夜不烘焙其中。
        self.rooms = {room.id: build_room_surface(room).convert() for room in level.rooms}

    # 按准备的字号生成文字，颜色由所在展示层明确指定。
    def render_text(self, text: str, size_pixels: int = 20,
                    color: tuple[int, int, int] = (224, 238, 230)) -> pygame.Surface:
        # 未缓存字号不是隐式逐帧创建资源的理由。
        if size_pixels not in self._fonts:
            # 调用者必须使用明确准备的字号。
            raise ValueError(f"Unprepared font size: {size_pixels}")
        # 字体渲染不读取外部文字文件或修改业务。
        return self._fonts[size_pixels].render(text, True, color)
