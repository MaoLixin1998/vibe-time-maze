# pygame只负责几何表现，不修改角色状态。
import pygame

# 用通用圆形玩家占位，正式vibe角色素材在之后单独验收。
def draw_player( surface: pygame.Surface, center: tuple[int, int],
                 age: str, cell_pixels: float) -> None:
    # 年龄影响占位大小，与模型能力状态一致。
    radius = max(7, int(cell_pixels * (0.24 if age == "child" else 0.32)))
    # 小型地面影子帮助看清当前格中心。
    pygame.draw.ellipse(surface, (53, 64, 61), (center[0] - radius, center[1] + radius // 2,
                                             radius * 2, max(4, radius // 2)))
    # 几何圆形不使用正式vibe外观特征。
    pygame.draw.circle(surface, (244, 206, 102), center, radius)
    # 外边描线在昼夜地板都保持可读。
    pygame.draw.circle(surface, (55, 72, 77), center, radius, 2)
    # 成年占位使用单一竖线区分，不加正式人物服装。
    if age == "adult":
        # 标记只是灰盒年龄指示。
        pygame.draw.line(surface, (81, 94, 89), (center[0], center[1] - radius // 2),
                         (center[0], center[1] + radius // 2), 2)
