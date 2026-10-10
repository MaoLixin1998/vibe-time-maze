# pygame只绘制出口展开，不推进世界时间。
import pygame
# 过场进度和年龄由不可变快照提供。
from time_maze.model.game_snapshot import GameSnapshot
# 字体资源由应用提前准备，绘制期间不读取磁盘。
from time_maze.rendering.resource_bundle import ResourceBundle
# 普通世界和旷野展开使用同一几何角色接口。
from time_maze.rendering.player_drawing import draw_player

# G出口使用几何旷野展开预演，动画结束仍由模型恢复玩家操作。
def draw_meadow_reveal(surface: pygame.Surface, snapshot: GameSnapshot,
                       resources: ResourceBundle) -> None:
    # 模型统一提供归一化过场进度，渲染不推进它。
    progress = snapshot.cutscene_progress
    # 天空背景独立于普通俯视地图。
    surface.fill((138, 196, 208))
    # 展开阶段逐渐提高地平线，表现抬高视角。
    horizon = int(440 - max(0.0, progress - 0.25) * 130)
    # 原创远山仅为背景，不添加第八个区域。
    pygame.draw.polygon(surface, (94, 137, 131), ((0, horizon + 20), (190, horizon - 100),
                        (370, horizon + 5), (570, horizon - 140), (820, horizon + 20),
                        (1010, horizon - 80), (1100, horizon + 20), (1100, 800), (0, 800)))
    # 近地面与背景分开。
    pygame.draw.rect(surface, (153, 180, 118), (0, horizon + 50, 1100, 800 - horizon))
    # 近洞初始较大，后撤期间同步缩小。
    scale = 1.0 - max(0.0, progress - 0.25) * 0.70
    # 洞口底部随视野展开向下偏移。
    center = (550, int(570 + progress * 35))
    # 低矮洞口保持非开放世界的出口表现。
    pygame.draw.ellipse(surface, (64, 80, 68), (center[0] - int(90 * scale),
                        center[1] - int(35 * scale), int(180 * scale), int(70 * scale)))
    # 前段出洞后站定，随后只缩放场景表现。
    player_y = center[1] + int(min(progress / 0.22, 1.0) * 62 * scale)
    # 角色是同一通用占位圆形，非正式vibe动画。
    draw_player(surface, (center[0], player_y), snapshot.age, 44 * scale)
    # 明确标注灰盒表现，Space由输入层调用正式跳过。
    surface.blit(resources.render_text("Meadow reveal - graybox presentation", 30,
                                       (35, 67, 63)), (275, 115))
    # 玩家过场结束后才可真实移动开箱。
    surface.blit(resources.render_text("Climb out, stop, reveal the meadow.  Space: skip", 20,
                                       (35, 67, 63)), (290, 160))
