# pygame绘图函数只生成基础几何资源，不读取私人图像。
import pygame
# 静态房间来自正式校验后的只读定义。
from time_maze.model.room_definition import RoomDefinition

# 基础网格像素尺寸是渲染单位，不参与业务碰撞。
TILE_PIXELS = 36
# 三键组合映射只表达既定七音的物理键高亮。
NOTE_BUTTONS = ((0,), (1,), (2,), (0, 1), (1, 2), (0, 2), (0, 1, 2))

# 创建一份中性静态地板，动态交互物与昼夜层后续独立绘制。
def build_room_surface(room: RoomDefinition) -> pygame.Surface:
    # 按实际房间尺寸创建不透明底图。
    surface = pygame.Surface((room.width * TILE_PIXELS, room.height * TILE_PIXELS))
    # 无地板格以墙体颜色表现，不额外创造通路。
    surface.fill((36, 47, 57))
    # 地板只按模型定义的合法格子绘制。
    for x, y in room.floors:
        # 棋格轻微明暗只帮助玩家判断网格位置。
        color = (167, 179, 167) if (x + y) % 2 else (174, 185, 175)
        # 鸡領地用暖土地色区分，边界不假称免疫区。
        if (x, y) in room.territory:
            # 地板视觉不会改变正式领地判定。
            color = (179, 164, 129) if (x + y) % 2 else (188, 174, 139)
        # 格子边缘留一像素明确静态地板边界。
        pygame.draw.rect(surface, color, (x * TILE_PIXELS, y * TILE_PIXELS,
                                         TILE_PIXELS - 1, TILE_PIXELS - 1))
    # 三层剑座边界来自正式布局数据，不能擅自在可走地板上加墙。
    for step_index, (left, top, right, bottom) in enumerate(room.pedestal_steps):
        # 边界格坐标包含末格，换成完整像素矩形。
        area = pygame.Rect(left * TILE_PIXELS, top * TILE_PIXELS,
                           (right - left + 1) * TILE_PIXELS, (bottom - top + 1) * TILE_PIXELS)
        # 层层升高的石面逐渐提亮，区别普通地板。
        stone_color = (113 + step_index * 22, 128 + step_index * 21, 137 + step_index * 20)
        # 绘制已经不可通行的大型石台，不新增碰撞条件。
        pygame.draw.rect(surface, stone_color, area)
        # 石座边缘与普通地板有明显界限。
        pygame.draw.rect(surface, (72, 91, 105), area, 5)
        # 前沿下缘亮线帮助辨认三层高差。
        pygame.draw.line(surface, (208, 218, 216), area.bottomleft, area.bottomright, 3)
        # 石块分缝只表达静态宏伟形体，不产生通路。
        for seam_x in range(area.left + TILE_PIXELS * 2, area.right, TILE_PIXELS * 2):
            # 竖缝在本层边界内终止。
            pygame.draw.line(surface, (96 + step_index * 13, 111 + step_index * 13, 122 + step_index * 13),
                             (seam_x, area.top + 4), (seam_x, area.bottom - 4), 1)
        # 横缝采用更大的块面，区别网格地板纹理。
        for seam_y in range(area.top + TILE_PIXELS * 2, area.bottom, TILE_PIXELS * 2):
            # 横缝不会改变floor集合。
            pygame.draw.line(surface, (96 + step_index * 13, 111 + step_index * 13, 122 + step_index * 13),
                             (area.left + 4, seam_y), (area.right - 4, seam_y), 1)
    # 固定地标只绘制石板，文字由Renderer使用字体绘制。
    for x, y, label in room.landmarks:
        # 稳定划痕在底图保留，切龄昼夜后仍可识别。
        center = (x * TILE_PIXELS + TILE_PIXELS // 2, y * TILE_PIXELS + TILE_PIXELS // 2)
        # 石板属于静态场景，与提示文字ID无关。
        pygame.draw.circle(surface, (95, 117, 110), center, TILE_PIXELS // 5)
        # 三条固定划痕帮助定位，不揭示未知管道答案。
        for line_index in range(3):
            # 同样长度的痕迹处于该地标格内。
            pygame.draw.line(surface, (214, 218, 181),
                             (center[0] - 7 + line_index * 5, center[1] - 4),
                             (center[0] - 5 + line_index * 5, center[1] + 4), 2)
    # 返回准备好的资源，后续绘制不会逐帧读取地图文件。
    return surface

# 用矢量画三键图标，避免依赖字体中的特殊符号。
def draw_button_icon(surface: pygame.Surface, button_index: int, center: tuple[int, int],
                     size_pixels: int, color: tuple[int, int, int]) -> None:
    # 图标半径与按钮尺寸成比例。
    radius = max(3, size_pixels // 4)
    # 上方长键展示语音图标，但并不调用真实麦克风。
    if button_index == 0:
        # 简单圆角矩形表示麦克风外形。
        pygame.draw.rect(surface, color, (center[0] - radius // 2, center[1] - radius,
                                         radius, radius * 2), 2, border_radius=radius // 2)
        # 托架与底座都是图形，不需要私有图标素材。
        pygame.draw.arc(surface, color, (center[0] - radius, center[1] - radius,
                                        radius * 2, radius * 2 + 4), 3.14, 6.28, 2)
        # 底座向下连接以便在缩略图中辨认。
        pygame.draw.line(surface, color, (center[0], center[1] + radius),
                         (center[0], center[1] + radius + 4), 2)
    # 左下键使用对勾图形。
    elif button_index == 1:
        # 三点折线保持与原三键布局一致。
        pygame.draw.lines(surface, color, False, ((center[0] - radius, center[1]),
                          (center[0] - 2, center[1] + radius // 2),
                          (center[0] + radius, center[1] - radius)), 3)
    # 右下键使用叉图形。
    else:
        # 第一条斜线形成叉的一半。
        pygame.draw.line(surface, color, (center[0] - radius, center[1] - radius),
                         (center[0] + radius, center[1] + radius), 3)
        # 第二条斜线完成叉。
        pygame.draw.line(surface, color, (center[0] - radius, center[1] + radius),
                         (center[0] + radius, center[1] - radius), 3)

# 绘制完整三键组合，七音之一只高亮所属物理键。
def draw_three_keys(surface: pygame.Surface, area: pygame.Rect, note_id: int | None,
                    is_small: bool = False) -> None:
    # 无最近音符时不高亮任何键。
    active_buttons = NOTE_BUTTONS[note_id - 1] if note_id is not None else ()
    # 上长键与下双键采用固定比例，不增加第四键。
    buttons = (pygame.Rect(area.x, area.y, area.width, int(area.height * 0.43)),
               pygame.Rect(area.x, area.y + int(area.height * 0.53),
                           int(area.width * 0.46), int(area.height * 0.43)),
               pygame.Rect(area.x + int(area.width * 0.54), area.y + int(area.height * 0.53),
                           int(area.width * 0.46), int(area.height * 0.43)))
    # 各键依据同一映射给出组合状态。
    for button_index, button in enumerate(buttons):
        # 按下色与默认色保持明显差异。
        color = (103, 220, 181) if button_index in active_buttons else (61, 81, 92)
        # 圆角按钮不绘制像钢琴的独立音高键。
        pygame.draw.rect(surface, color, button, border_radius=4 if is_small else 14)
        # 图标大小适配组合缩略图。
        draw_button_icon(surface, button_index, button.center,
                         min(button.width, button.height), (230, 245, 237))
