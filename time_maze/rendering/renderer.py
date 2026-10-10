# 正式文字映射只读注入，不能由显示文字反推世界状态。
from collections.abc import Mapping
# 独立只读副本避免调用者更改展示资源。
from types import MappingProxyType
# pygame负责基础几何展示，模型不反向依赖此模块。
import pygame
# 正式地图决定区域尺寸与静态拓扑。
from time_maze.model.level_definition import LevelDefinition
# 所有移动和追逐参数来自同一正式规则。
from time_maze.model.rules_definition import RulesDefinition
# 交互物定义给出真实位置与独立运行状态。
from time_maze.model.interactive_object import InteractiveObject
# 游戏与输入展示都使用不可变快照。
from time_maze.model.game_snapshot import GameSnapshot
# 输入快照不要求渲染持有控制器。
from time_maze.model.keyboard_snapshot import KeyboardSnapshot
# 门的表现使用与真实通行相同的公开查询。
from time_maze.model.transition_rules import portal_access
# 已准备资源由应用显式创建和传入。
from time_maze.rendering.resource_bundle import ResourceBundle
# 基础三键图示不使用私人图像或特殊字体符号。
from time_maze.rendering.generated_resources import draw_three_keys
# 动态玩家占位共用公开绘制接口。
from time_maze.rendering.player_drawing import draw_player
# G的专属运镜独立维护，共用渲染器只负责组合。
from time_maze.rendering.areas.meadow_reveal import draw_meadow_reveal

# 正式窗口默认尺寸留足地图、提示与键盘曲谱空间。
WINDOW_SIZE = (1100, 800)
# 必要英文条件与正式条件ID对应，开闭真假仍来自portal_access。
CONDITION_TEXT = {"open": "Both ages / day and night", "child": "Child only",
                  "cargo": "Push from below as adult", "night": "Night only",
                  "child_day": "Child + daytime"}
# 当前展示层的稳定配色，不参与游戏规则。
TEXT_COLOR = (227, 238, 232)
# 操作提示颜色保证与暗色背景有足够差异。
ACCENT_COLOR = (103, 220, 181)

# Renderer只绘制快照，不推进时间、不修改输入或世界。
class Renderer:
    # 持有准备完成的资源与静态定义，应用仍拥有窗口生命周期。
    def __init__(self, screen: pygame.Surface, level: LevelDefinition,
                 rules: RulesDefinition, resources: ResourceBundle,
                 text: Mapping[str, str] | None = None) -> None:
        # 屏幕由Application创建，本对象不关闭它。
        self._screen = screen
        # 静态地图与规则都是已校验的只读定义。
        self._level = level
        # 曲谱展示和正式匹配共用同一规则输入。
        self._rules = rules
        # 资源缓存不在绘制期间重新加载。
        self._resources = resources
        # 复制后冻结外部文字；未注入时必要基础英语仍可运行。
        self._text_mapping = MappingProxyType(dict(text or {}))
        # 普通房间复用一个全屏绘图缓冲。
        self._world = pygame.Surface(screen.get_size())
        # 面板背景模糊通过缩放缓冲实现，不读取屏幕截图。
        self._blur_size = (max(1, screen.get_width() // 12), max(1, screen.get_height() // 12))

    # 统一文本绘制，最长宽度防止世界提示覆盖HUD边界。
    def _text(self, surface: pygame.Surface, text: str, position: tuple[int, int],
              size_pixels: int = 20, color: tuple[int, int, int] = TEXT_COLOR,
              max_width: int | None = None,
              background: tuple[int, int, int] | None = None) -> None:
        # 先使用准备完成的字体渲染。
        rendered = self._resources.render_text(text, size_pixels, color)
        # 过长说明在明确区域内缩小，不隐藏必要状态。
        if max_width is not None and rendered.get_width() > max_width:
            # 按原宽高比例缩放，至少保留一像素高度。
            height = max(1, int(rendered.get_height() * max_width / rendered.get_width()))
            # 只缩放当前文字图像，不改变字体缓存。
            rendered = pygame.transform.smoothscale(rendered, (max_width, height))
        # 地标可用实色底板保持昼夜对比，底板不参与碰撞。
        if background is not None:
            # 与实际文字尺寸一致，避免覆盖大块通行空间。
            area = pygame.Rect(position[0] - 3, position[1] - 2, rendered.get_width() + 6, rendered.get_height() + 4)
            # 圆角底板明确是文字标牌而非实体墙。
            pygame.draw.rect(surface, background, area, border_radius=3)
        # 写入指定层，文字绘制没有模型副作用。
        surface.blit(rendered, position)

    # 中文字体缺失时从正式文字键获取英语目的地或地标。
    def _label(self, text_id: str, preferred: str, fallback: str) -> str:
        # 可显示中文的系统沿用正式布局已有名称。
        if self._resources.has_cjk_font or preferred.isascii():
            # 可读名称只作展示，不参与通行判定。
            return preferred
        # 无系统中文字体时使用明确注入的正式英语标签。
        return self._text_mapping.get(text_id, fallback)

    # 正式提示按字体能力选用同一文字ID的中文或英语版本。
    def _message(self, text_id: str, fallback: str) -> str:
        # 首选正式中文或本身可由默认字体显示的ASCII文字。
        preferred = self._text_mapping.get(text_id, "")
        # 系统字体具备能力时沿用正式文字来源。
        if preferred and (self._resources.has_cjk_font or preferred.isascii()):
            # 文案仅用于展示，不决定任何世界行为。
            return preferred
        # 清洁安装环境依靠正式英语文字和必要内置默认提示。
        return self._text_mapping.get(f"{text_id}_en", fallback)

    # 从已收录曲谱中比较前缀，返回下一音或实际首个错音位置。
    def _phrase_feedback(self, snapshot: GameSnapshot, keyboard: KeyboardSnapshot) -> tuple[str, tuple[int, int] | None]:
        # 只有已经取得的谱可用于提示，不能泄露未收录旋律。
        melodies = tuple(melody for melody in self._rules.melodies if melody.id in snapshot.collected_scores)
        # 没有已取得谱时不比较隐藏数据。
        if not melodies:
            # 探索提示在谱册区另行显示。
            return "", None
        # 完整前缀匹配可得到同源下一步组合。
        matches = tuple(melody for melody in melodies if keyboard.notes == melody.notes[:len(keyboard.notes)])
        # 多谱都匹配空前缀时优先主线，不自动填入或播放。
        if matches:
            # 稳定主线优先，仅作提示选择。
            melody = next((melody for melody in matches if melody.category == "main"), matches[0])
            # 已输入全部音符时仍需玩家明确Enter提交。
            if len(keyboard.notes) == len(melody.notes):
                # 不能将未提交输入伪装成世界效果。
                return "Complete phrase - Enter to submit", None
            # 下一音来自正式已取得曲谱，不另写一套旋律。
            next_note = melody.notes[len(keyboard.notes)]
            # 数字及八度提示与图示同源。
            return f"Next: {'^' if next_note[1] else ''}{next_note[0]} - follow the highlighted combination", next_note
        # 每张已取得谱计算实际共享前缀长度。
        prefix_lengths = []
        # 曲谱数很少，不需要维护额外可变业务状态。
        for melody in melodies:
            # 从首音开始找首个真实不匹配。
            matched_count = 0
            # zip只比较两者实际都存在的音符。
            for actual, expected in zip(keyboard.notes, melody.notes):
                # 八度和音符均须一致，不能默认为正确。
                if actual != expected:
                    # 该位置是此谱首个错音。
                    break
                # 连续前缀已有一音真实匹配。
                matched_count += 1
            # 同源谱及前缀长度作为本帧独立结果。
            prefix_lengths.append((matched_count, melody))
        # 选择最接近的已取得谱来定位错误，而不是自动纠错。
        matched_count, melody = max(prefix_lengths, key=lambda item: item[0])
        # 超过完整谱长度也属于明确的前缀输入错误。
        if matched_count >= len(melody.notes):
            # 不偷偷截断额外音符。
            return f"Extra note at position {matched_count + 1} - Backspace clears the phrase", None
        # 第一处错误使用一基位置，方便玩家按曲谱核对。
        return f"Wrong note at position {matched_count + 1} - check note and octave", None

    # 计算地图视口，静态与动态对象使用完全相同的坐标变换。
    def _room_transform(self, region: str) -> tuple[float, int, int]:
        # 查询已经校验的房间定义。
        room = self._level.room(region)
        # 地图在上下HUD之间居中留边。
        available_width = self._screen.get_width() - 70
        # 提示区保持不被夜间层遮暗。
        available_height = self._screen.get_height() - 270
        # 同比例缩放确保每格在横纵轴尺寸一致。
        cell_pixels = min(available_width / room.width, available_height / room.height)
        # 左侧居中偏移单位为像素。
        offset_x = int((self._screen.get_width() - cell_pixels * room.width) / 2)
        # 地图顶端从120像素开始，额外空白上下平分。
        offset_y = int(112 + (available_height - cell_pixels * room.height) / 2)
        # 三个值都仅用于显示。
        return cell_pixels, offset_x, offset_y

    # 将格坐标映射至格中心，支持模型给出的插值位置。
    def _point(self, position: tuple[float, float], transform: tuple[float, int, int]) -> tuple[int, int]:
        # 同一坐标变换用于门、玩家、鸡和交互物。
        cell_pixels, offset_x, offset_y = transform
        # 位置加半格使圆形对象位于地板中心。
        return int(offset_x + (position[0] + 0.5) * cell_pixels), int(offset_y + (position[1] + 0.5) * cell_pixels)

    # 绘制单张中性底图及独立状态层，地图不复制为四种年龄昼夜版本。
    def _draw_world(self, snapshot: GameSnapshot) -> None:
        # 先清空上帧像素，避免跨区残影。
        self._world.fill((20, 29, 39))
        # 当前房间来自模型已经提交的区域。
        room = self._level.room(snapshot.region)
        # 统一变换保证碰撞边界与表现对应。
        transform = self._room_transform(snapshot.region)
        # 解包格大小及左上角。
        cell_pixels, offset_x, offset_y = transform
        # 底图只缩放已生成资源，不在此阶段生成新布局。
        size = (max(1, int(room.width * cell_pixels)), max(1, int(room.height * cell_pixels)))
        # 保存中性底图到世界层。
        self._world.blit(pygame.transform.smoothscale(self._resources.rooms[room.id], size),
                         (offset_x, offset_y))
        # 门按正式条件查询表现开启或关闭。
        for portal in room.portals:
            # 查询共用规则而不在界面重新实现条件判定。
            is_held = (snapshot.region, portal.position) in snapshot.held_thresholds
            # 门槛占用者切昼后仍可安全离开，表现与碰撞共源。
            is_open, reason = portal_access(portal, snapshot.age, snapshot.is_day, snapshot.box_open, is_held)
            # 门槛本身是地图定义中的格子。
            center = self._point(portal.position, transform)
            # 青色开放、红棕关闭，旁边仍展示真实条件。
            color = ACCENT_COLOR if is_open else (197, 115, 93)
            # 门框与地板分开，闭门不会被误认为普通地面。
            area = pygame.Rect(0, 0, max(12, int(cell_pixels * 0.88)), max(12, int(cell_pixels * 0.88)))
            # 门框放在指定格中心。
            area.center = center
            # 轮廓避免覆盖玩家所在门槛。
            pygame.draw.rect(self._world, color, area, 3, border_radius=4)
            # 箭头标记跨门方向，不泄露目标区域代号。
            dx, dy = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}[portal.direction]
            # 箭头线段按格大小缩放。
            tip = (center[0] + int(dx * cell_pixels * 0.3), center[1] + int(dy * cell_pixels * 0.3))
            # 开闭状态仍由同一颜色表达。
            pygame.draw.line(self._world, color, center, tip, 3)
        # 独立物件按真实运行状态绘制，不烘焙进地板。
        for item in room.objects:
            # 每个对象只持有静态定义，状态来自快照。
            self._draw_object(item, snapshot, transform)
        # 鸡的位置与行为完全来自当前时代快照。
        for chicken_region, x, y, mode in snapshot.chickens:
            # 不把其他房间的鸡叠加到当前画面。
            if chicken_region == snapshot.region:
                # 动态鸡与底图分开，可独立归巢。
                self._draw_chicken(self._point((x, y), transform), mode, cell_pixels)
        # 出口展开有独立几何演示，普通玩家只在正常房间画一次。
        draw_player(self._world, self._point(snapshot.visual_pos, transform),
                          snapshot.age, cell_pixels)
        # 主要昼夜光照落在鸡領地区域，HUD在之后独立画。
        if not snapshot.is_day and room.territory:
            # 逐通道冷色乘法覆盖世界层，避免原生驱动透明格式差异。
            darkness = pygame.Surface(self._world.get_size())
            # 夜色保留地板和鸡的可读轮廓。
            darkness.fill((133, 151, 191))
            # 仅暗化世界层。
            self._world.blit(darkness, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        # 标牌在昼夜滤镜之后独立绘制，字体缺失或夜色不能抹掉线索，不把字体缺失变成线索消失。
        for x, y, label in room.landmarks:
            # 坐标是静态布局标识，映射只负责同一地标的展示语言。
            text_id = f"landmark_{room.id.lower()}_{x}_{y}"
            # 正式文字可描述脚印、竹结等，不揭示未知洞答案。
            display_label = self._label(text_id, label, "Landmark")
            # 位置与底图划痕格保持同源。
            center = self._point((x, y), transform)
            # 标签不改变碰撞或门条件。
            self._text(self._world, display_label, (center[0] - 35, center[1] + 12), 16,
                       (234, 241, 215), 160, background=(30, 45, 48))
        # 滑落过场用网格占位动画提示，不能冒称正式角色动画。
        if snapshot.phase == "sliding":
            # 限定在世界视口展示状态提示。
            self._text(self._world, "Sliding into the maze...", (320, 360), 30)

    # 单独绘制动态物件；几何外形是可替换的灰盒表现。
    def _draw_object(self, item: InteractiveObject, snapshot: GameSnapshot,
                     transform: tuple[float, int, int]) -> None:
        # 静态坐标由正式地图定义提供。
        center = self._point(item.position, transform)
        # 每个物件尺寸随格子缩放。
        size = max(10, int(transform[0] * 0.62))
        # 货箱拥有业务进度，底图中不包含箱子。
        if item.kind == "cargo_box":
            # 当前箱位置由模型路径与进度共同生成，不在界面捏造停放格。
            center = self._point(snapshot.box_visual_pos, transform)
            # 货箱作为可见几何重物，不画轨道。
            area = pygame.Rect(0, 0, size, size)
            # 当前插值位置不回写碰撞。
            area.center = center
            # 主体木色区分于门框与地面。
            pygame.draw.rect(self._world, (120, 85, 48), area, border_radius=3)
            # 交叉木板强调可推物，不增加第二块阻挡。
            pygame.draw.line(self._world, (201, 159, 94), area.topleft, area.bottomright, 3)
            # 第二条木板补充重量感。
            pygame.draw.line(self._world, (201, 159, 94), area.topright, area.bottomleft, 3)
        # 剑台始终存在，剑身独立由当前年龄状态表现。
        elif item.kind == "sword":
            # 三层巨大静态石台已由基础底图按正式布局绘制。
            # 少年态显示插入剑台的剑。
            if snapshot.age == "child":
                # 剑刃是独立动态线段。
                pygame.draw.line(self._world, (229, 241, 245), (center[0], center[1] - size),
                                 (center[0], center[1] + size // 3), 4)
                # 横护手不使用原作资产。
                pygame.draw.line(self._world, (220, 172, 85), (center[0] - 7, center[1] - 8),
                                 (center[0] + 7, center[1] - 8), 4)
        # 谱箱与奖励箱分别读取各自业务开合状态。
        elif item.kind in {"score_chest", "score", "reward_chest", "reward"}:
            # 奖励箱领取不由谱册集合判断。
            is_open = snapshot.reward_claimed if item.kind in {"reward_chest", "reward"} else item.id in snapshot.opened_chests
            # 箱子外形与货箱明显区分。
            area = pygame.Rect(0, 0, size + 4, max(10, size * 3 // 4))
            # 中心按地图位置放置。
            area.center = center
            # 已开箱呈现更暗色并开启盖子。
            pygame.draw.rect(self._world, (132, 91, 44) if is_open else (212, 153, 55), area, border_radius=3)
            # 锁扣是物件内部图形，不改变交互距离。
            pygame.draw.rect(self._world, (244, 224, 153), (center[0] - 2, center[1] - 4, 4, 8))
            # 开启箱盖用独立线段表达。
            if is_open:
                # 箱盖上移保持可见已领取状态。
                pygame.draw.line(self._world, (220, 175, 86), (area.left, area.top - 6),
                                 (area.right, area.top - 6), 4)
        # 鸡巢是独立层，不烘焙进夜间地图。
        elif item.kind == "nest":
            # 鸡窝采用简单椭圆而非私人图像。
            pygame.draw.ellipse(self._world, (138, 105, 57),
                                (center[0] - size, center[1] - size // 2, size * 2, size))
        # 邻近可交互物提供统一E引导，种类决定用途。
        if item.kind != "nest" and abs(item.position[0] - snapshot.pos[0]) + abs(item.position[1] - snapshot.pos[1]) <= 1:
            # 不完整显示未开箱谱内容。
            action = "E: interact" if item.kind != "sword" else "E: change age"
            # 图上小提示与HUD大说明互补。
            self._text(self._world, action, (center[0] + size + 7, center[1] - 8), 16,
                       (29, 53, 47), 160)

    # 鸡的动态颜色与轮廓反馈警告、追逐及归巢状态。
    def _draw_chicken(self, center: tuple[int, int], mode: str, cell_pixels: float) -> None:
        # 圆形鸡大小不会改变模型追逐或碰撞。
        radius = max(5, int(cell_pixels * 0.23))
        # 追逐状态给明显红色轮廓。
        color = (249, 128, 109) if mode in {"chasing", "warning"} else (233, 231, 200)
        # 独立鸡体不与巢合并。
        pygame.draw.circle(self._world, color, center, radius)
        # 黄色三角嘴让灰盒鸡可辨认。
        pygame.draw.polygon(self._world, (245, 190, 54), ((center[0] + radius - 1, center[1] - 2),
                            (center[0] + radius + 6, center[1]), (center[0] + radius - 1, center[1] + 3)))
        # 警告先于追逐用可见感叹号替代听音依赖。
        if mode == "warning":
            # 静音玩家也能识别警戒窗口。
            self._text(self._world, "!", (center[0] - 4, center[1] - radius - 20), 24,
                       (255, 235, 143))
        # 归巢状态以细绿色圈表示路线线索。
        elif mode in {"returning", "return"}:
            # 轮廓不标未知排水口答案。
            pygame.draw.circle(self._world, ACCENT_COLOR, center, radius + 3, 2)

    # HUD必要信息保持英文，系统中文字体只提供附加真实业务文字。
    def _draw_hud(self, snapshot: GameSnapshot, keyboard: KeyboardSnapshot,
                  audio_status: str) -> None:
        # HUD背景与昼夜世界层分别绘制。
        pygame.draw.rect(self._screen, (16, 26, 37), (0, 0, self._screen.get_width(), 100))
        # 人类可读区域名称不显示A到G调试代号。
        name = self._level.room(snapshot.region).name
        # 没有中文字体时用稳定用途名称保证区域可识别。
        if not self._resources.has_cjk_font and not name.isascii():
            # 用途标签不改变正式区域ID。
            name = self._text_mapping.get(f"room_{snapshot.region.lower()}_en", "Maze area")
        # 顶部展示年龄与游戏年份，日期不从系统读。
        self._text(self._screen, name, (30, 20), 30)
        # 昼夜与年龄状态来自同一快照。
        self._text(self._screen, f"{snapshot.age.title()} / {snapshot.year}  |  {'DAY' if snapshot.is_day else 'NIGHT'}",
                   (650, 24), 24, ACCENT_COLOR)
        # 基础操作必要信息始终可见。
        self._text(self._screen, self._message("controls", "WASD / arrows: move   E: interact   K: instrument   Esc: close / pause   F5: NEW GAME"),
                   (30, 68), 18, (177, 195, 191), 1030)
        # 世界下方反馈区不被夜间层遮暗。
        pygame.draw.rect(self._screen, (16, 26, 37), (0, 655, 1100, 145))
        # 当前阶段选择实际可用操作提示。
        instruction = {"intro": "Approach the sword and press E. Your age changes at the sword pedestal.",
                       "exploring": "Explore landmarks. Chests record scores. Nearby doors show their travel conditions.",
                       "sliding": "Sliding into the maze. The transition ends automatically.",
                       "pushing": "The adult pushes the heavy crate north. The movement ends automatically.",
                       "exit_reveal": "You crossed the real exit. Pursuit ended. Space skips the reveal.",
                       "reward": "The meadow is safe. Walk to the reward chest and press E.",
                       "failed": "Caught! R restores the complete checkpoint. F5 starts a completely new game."}[snapshot.phase]
        # 已领取奖励后展示当前实际可用动作，不再要求再次开箱。
        if snapshot.reward_claimed:
            # 奖励状态独立于通关，并由公开快照提供。
            instruction = "Rewards claimed. Keep exploring the meadow, or F5 starts a new game."
        # 主阶段提示实际消费正式文字，未配置的阶段有必要英语默认。
        instruction = self._message("phase_reward_claimed" if snapshot.reward_claimed else f"phase_{snapshot.phase}", instruction)
        # 玩家必要操作在无中文字体情况下仍完整可读。
        self._text(self._screen, instruction, (30, 674), 20, TEXT_COLOR, 1030)
        # 邻近通行条件在固定HUD区域展示，避免浮动文字遮住玩家与危险。
        portals = [portal for portal in self._level.room(snapshot.region).portals
                   if abs(portal.position[0] - snapshot.pos[0]) + abs(portal.position[1] - snapshot.pos[1]) <= 2]
        # 有邻近门时使用真实共源查询生成英语条件。
        if portals:
            # 同一区内只展示距离最近的门，不揭示未知出口目标。
            portal = min(portals, key=lambda value: abs(value.position[0] - snapshot.pos[0]) + abs(value.position[1] - snapshot.pos[1]))
            # 当前占用门槛允许安全离开。
            is_held = (snapshot.region, portal.position) in snapshot.held_thresholds
            # 查询与模型碰撞相同的条件及实际开闭结果。
            is_open, reason = portal_access(portal, snapshot.age, snapshot.is_day, snapshot.box_open, is_held)
            # 条件名称本身只说明用途，不揭示迷宫答案。
            condition = CONDITION_TEXT[portal.condition]
            # 占用延迟关门需要明确说明离开后才关闭。
            if portal.condition == "night" and snapshot.is_day and is_held:
                # 该显示来自实际占用状态。
                condition = "Safe to leave; closes after leaving"
            # 开通货路不再错误要求重复推动。
            elif portal.condition == "cargo" and is_open:
                # 真正开通状态来自快照。
                condition = "Passage cleared / both ages"
            # 目的地或排水口地标来自正式文字，未知洞不展示目标区域答案。
            destination = self._label(f"portal_{portal.id}", portal.label, "Passage")
            # OPEN/CLOSED与门框颜色、正式通行条件一致。
            self._text(self._screen, f"{destination}: {condition} [{'OPEN' if is_open else 'CLOSED'}]",
                       (30, 708), 18, ACCENT_COLOR, 1010)
        # 无邻近门时显示真实最后结果英文ID，保证无中文字体仍可读。
        elif snapshot.events:
            # 最近事件属于真实操作，不伪造识别成功。
            last_event = snapshot.events[-1]
            # 字符串转换只作用于显示。
            self._text(self._screen, last_event.kind.replace("_", " ").title(), (30, 708), 18, ACCENT_COLOR)
        # 摇篮谱可能先拿到，缺时间谱提示必须独立于其他已收录曲。
        if "time_shift" not in snapshot.collected_scores and snapshot.phase in {"intro", "exploring"}:
            # 提示回迷宫找真实谱箱，不在门牌直接发完整旋律。
            self._text(self._screen, self._message("time_score_hint", "Time score missing: return to Maze crossroads and search the long passages."),
                       (30, 733), 16, (247, 213, 149), 1010)
        # 实际模型反馈有中文字体时作为额外说明，不解析文字反推状态。
        if self._resources.has_cjk_font and ("time_shift" in snapshot.collected_scores or snapshot.phase not in {"intro", "exploring"}):
            # 邻近提示与真实通行规则由模型提供。
            hint = snapshot.nearby_hint or snapshot.message
            # 中文附加行与英语必要信息均不遮挡世界。
            self._text(self._screen, hint, (30, 733), 16, (179, 204, 192), 1010)
        # 音频降级与灰盒版本共用底部附加状态行。
        status = audio_status or self._message("graybox", "Synthesized flute / one note per combination / no rhythm requirement")
        # 设备原因可能很长，在HUD宽度内显示。
        self._text(self._screen, status, (30, 757), 16, (155, 174, 174), 1030)
        # 领奖明确显示两件既定奖励，占位表现不改变领取状态。
        if snapshot.reward_claimed:
            # 收到奖励之后仍允许在G移动。
            self._text(self._screen, self._message("reward", "Reward: Switch 2 + The Legend of Zelda: Ocarina of Time"), (150, 610),
                       24, (255, 238, 152), 830)

    # 三键面板只展示已收录完整谱，基础组合表始终可查。
    def _draw_keyboard(self, snapshot: GameSnapshot, keyboard: KeyboardSnapshot,
                       audio_status: str) -> None:
        # 先将世界缩小再放大，形成虚化背景而不暂停世界。
        blurred = pygame.transform.smoothscale(self._world, self._blur_size)
        # 面板之外的HUD保持清晰。
        self._screen.blit(pygame.transform.smoothscale(blurred, self._screen.get_size()), (0, 0))
        # 透明遮罩增强面板文字对比。
        shade = pygame.Surface(self._screen.get_size(), pygame.SRCALPHA)
        # 世界仍然更新，只改变视觉表现。
        shade.fill((8, 20, 30, 130))
        # 将暗层叠加在模糊世界。
        self._screen.blit(shade, (0, 0))
        # 主面板在窗口内留出固定安全边距。
        panel = pygame.Rect(40, 115, 710, 540)
        # 圆角实体色避免曲谱文字被背景干扰。
        pygame.draw.rect(self._screen, (25, 43, 56), panel, border_radius=20)
        # 标题告诉玩家打开面板不会暂停鸡群。
        self._text(self._screen, "VIBE three-key instrument", (65, 140), 30)
        # 前缀提交、音区及世界运行规则都明确可见。
        self._text(self._screen, "1-7: notes  |  Shift: high  |  Enter: submit  |  Backspace: clear  |  K / Esc: close",
                   (65, 185), 16, (182, 204, 199), 655)
        # 公平性需要玩家知道警戒仍在运行。
        self._text(self._screen, "WORLD KEEPS RUNNING - listen and watch for chicken warnings", (65, 212), 16,
                   (249, 213, 144), 655)
        # 近期音符才保持三键高亮。
        note_id = keyboard.last_note[0] if keyboard.last_note is not None and keyboard.last_note_seconds < 0.7 else None
        # 三键造型遵守上长键下双键，不展示第四键。
        key_area = pygame.Rect(65, 262, 175, 155)
        # 基础图示由统一组合映射绘制。
        draw_three_keys(self._screen, key_area, note_id)
        # 最近一音按组合给彩色涟漪，展示计时不推进业务。
        if note_id is not None and keyboard.last_note_seconds < 0.45:
            # 涟漪半径随时间扩张。
            radius = int(25 + keyboard.last_note_seconds * 135)
            # 高音与基础音区使用不同反馈色。
            color = (148, 191, 252) if keyboard.last_note[1] else ACCENT_COLOR
            # 同一音只画一圈，不被误解为多音和弦。
            pygame.draw.circle(self._screen, color, key_area.center, radius, 2)
        # 当前输入前缀使用数字及高八度标记。
        phrase = "  ".join(f"{'^' if octave else ''}{note}" for note, octave in keyboard.notes)
        # 未输入时提供必要指引。
        self._text(self._screen, phrase or "Play a complete phrase", (280, 265), 30, (244, 236, 186), 435)
        # 前缀容量来自规则而不写死。
        self._text(self._screen, f"{len(keyboard.notes)} / {self._rules.max_notes} notes  |  ^ = one octave higher",
                   (280, 307), 18, (172, 192, 190), 435)
        # 输入边界反馈独立于模型反馈。
        if keyboard.feedback:
            # 不把未提交前缀当成成功音乐。
            self._text(self._screen, keyboard.feedback, (280, 339), 16, (244, 193, 136), 435)
        # 已收录谱的前缀匹配给出下一音图示或实际错音位置。
        phrase_feedback, next_note = self._phrase_feedback(snapshot, keyboard)
        # 超限等输入边界反馈优先保留，避免一行文字互相覆盖。
        if phrase_feedback and not keyboard.feedback:
            # 提示不会改写前缀或自动触发提交。
            self._text(self._screen, phrase_feedback, (280, 344), 16,
                       (248, 217, 143) if next_note is None else ACCENT_COLOR, 435)
        # 基础七音组合始终可查，不需要谱箱才能看按法。
        for note_index in range(7):
            # 每个缩略图展示一条完整组合。
            area = pygame.Rect(285 + note_index * 63, 382, 45, 34)
            # 图形映射与大三键图一致。
            draw_three_keys(self._screen, area, note_index + 1, is_small=True)
            # 下一音的组合有独立外框，与当前按键高亮分开。
            if next_note is not None and next_note[0] == note_index + 1:
                # 图示来源于已取得曲谱，八度由上方数字提示明确。
                pygame.draw.rect(self._screen, (248, 222, 149), area.inflate(8, 8), 2, border_radius=4)
            # 音符数字和组合图处于同一列。
            self._text(self._screen, str(note_index + 1), (area.x + 18, 429), 18)
        # 只根据收录集合筛选真实曲谱。
        melodies = [melody for melody in self._rules.melodies if melody.id in snapshot.collected_scores]
        # 时间谱尚未取得时，无论有没有彩蛋谱都明确给出回程探索提示。
        if "time_shift" not in snapshot.collected_scores:
            # 不泄露完整旋律，玩家必须真实找到长死胡同谱箱。
            self._text(self._screen, self._message("time_score_hint", "Missing time score: return to Maze crossroads and search the long passages."),
                       (65, 456), 16, (248, 218, 158), 655)
        # 谱册为空也不会直接赠谱。
        if not melodies:
            # 未领取状态来自真实收录集合。
            self._text(self._screen, "No scores collected yet.", (65, 505), 20, ACCENT_COLOR, 655)
        # 每张收录谱按同一规则数据生成数字和组合图。
        for row_index, melody in enumerate(melodies):
            # 两箱谱最多两行，固定布局不混入其他未锁定五首。
            row_y = 481 + row_index * 77
            # 曲目名称来自正式运行数据，可无中文字体使用英文ID兜底。
            name = melody.name if self._resources.has_cjk_font or melody.name.isascii() else melody.id.replace("_", " ")
            # 可选曲与主线用途清晰区分。
            self._text(self._screen, f"{name} ({'optional' if melody.category != 'main' else 'day / night'})",
                       (65, row_y), 18, ACCENT_COLOR, 220)
            # 每音表示基础数字、必要八度和物理组合。
            for note_index, (note, octave) in enumerate(melody.notes):
                # 六音短句在面板右侧同宽排列。
                x = 305 + note_index * 65
                # 数字高音前缀不会误写成另一个音符。
                self._text(self._screen, f"{'^' if octave else ''}{note}", (x + 14, row_y), 18)
                # 组合图与正式音符顺序同源。
                draw_three_keys(self._screen, pygame.Rect(x, row_y + 24, 45, 32), note, is_small=True)
        # 实时世界小视图保留玩家、门与鸡位置，面板不能遮掉实际危险。
        room = self._level.room(snapshot.region)
        # 只截取已经绘好的地图层，不读取系统屏幕或改变模型。
        cell_pixels, offset_x, offset_y = self._room_transform(snapshot.region)
        # 地图区域来自同一坐标变换，避免小视图错位。
        bounds = pygame.Rect(offset_x, offset_y, int(room.width * cell_pixels), int(room.height * cell_pixels))
        # 固定小视图可用尺寸留出警戒文字。
        zoom = min(290 / bounds.width, 345 / bounds.height)
        # 同比例缩放不扭曲格子或碰撞关系。
        live_size = (max(1, int(bounds.width * zoom)), max(1, int(bounds.height * zoom)))
        # 小视图居中于面板右侧安全区域。
        live_area = pygame.Rect(775 + (290 - live_size[0]) // 2, 160, *live_size)
        # 标题明确显示实时世界而非静态地图。
        self._text(self._screen, "LIVE WORLD", (775, 126), 20, ACCENT_COLOR)
        # 正常世界画面在这里保持清晰，主背景仍然模糊。
        self._screen.blit(pygame.transform.smoothscale(self._world.subsurface(bounds), live_size), live_area)
        # 小视图有清晰边框避免被误当成装饰贴纸。
        pygame.draw.rect(self._screen, ACCENT_COLOR, live_area, 2)
        # 当前区域的真实鸡行为决定危险文字。
        modes = {mode for region, x, y, mode in snapshot.chickens if region == snapshot.region}
        # 追逐警告置于小视图下方，不被曲谱覆盖。
        if "chasing" in modes:
            # 世界运行时明确要求玩家结束演奏后逃跑。
            self._text(self._screen, "CHICKENS ARE CHASING!", (775, 525), 20, (255, 157, 130), 295)
            # 关闭面板即可恢复真实移动输入。
            self._text(self._screen, "K / Esc: close - move to escape", (775, 555), 18, TEXT_COLOR, 290)
        # 警告先于追逐，静音玩家也能立刻看到。
        elif "warning" in modes:
            # 不虚构剩余倒计时，全部取实际模式。
            self._text(self._screen, "CHICKEN WARNING!", (775, 525), 20, (255, 226, 139), 290)
            # 真实警告窗口内玩家可以关闭面板。
            self._text(self._screen, "K / Esc: close before they chase", (775, 555), 18, TEXT_COLOR, 290)
        # 夜间归巢只作为实际行为线索。
        elif "returning" in modes:
            # 不直接揭示正确管道答案。
            self._text(self._screen, "Chickens returning to nests", (775, 525), 18, ACCENT_COLOR, 290)
        # 没有危险时仍说明小视图保持运行。
        else:
            # 不把整个房间宣称为安全免疫区。
            self._text(self._screen, "Watch the live world", (775, 525), 18, TEXT_COLOR, 290)
        # HUD覆盖面板背景上方，年龄昼夜与警戒仍有实际更新。
        self._draw_hud(snapshot, keyboard, audio_status)

    # 单帧只绘图，传入只读快照与音频状态，不拥有任何控制器。
    def draw(self, snapshot: GameSnapshot, keyboard: KeyboardSnapshot,
             audio_status: str = "") -> None:
        # 出口演出与正常俯视地图分开选择。
        if snapshot.phase == "exit_reveal":
            # 该几何预演遵守先出洞后展开的正式流程。
            draw_meadow_reveal(self._world, snapshot, self._resources)
        # 其他阶段共享一套网格世界展示。
        else:
            # 昼夜、动态交互物与鸡群独立叠加。
            self._draw_world(snapshot)
        # 世界层完成后复制到应用持有的显示面。
        self._screen.blit(self._world, (0, 0))
        # 面板虚化世界但不决定时间是否推进。
        if keyboard.is_open:
            # 所有输入展示来自独立不可变快照。
            self._draw_keyboard(snapshot, keyboard, audio_status)
        # 关闭面板时直接显示HUD。
        else:
            # HUD不被夜间滤镜改变。
            self._draw_hud(snapshot, keyboard, audio_status)
        # 摇篮曲彩蛋只呈现可见几何星光，不改世界条件。
        if snapshot.events and snapshot.events[-1].kind == "egg_lullaby":
            # 彩蛋回应位于独立顶部卡片，不能被邻近门提示或谱册遮住。
            toast = pygame.Rect(355, 12, 270, 44)
            # 提供明显背景与边框，不只依赖声音。
            pygame.draw.rect(self._screen, (54, 57, 49), toast, border_radius=8)
            # 细金边保持与普通状态文字区分。
            pygame.draw.rect(self._screen, (240, 214, 139), toast, 1, border_radius=8)
            # 短回应不改变门、年龄、昼夜或通关状态。
            self._text(self._screen, self._message("lullaby", "A familiar lullaby..."), (368, 22), 18, (248, 220, 131), 210)
            # 小星光使用自制矢量，避免导入原游戏资产。
            pygame.draw.polygon(self._screen, (248, 220, 131), ((605, 19), (608, 26),
                                (616, 26), (610, 31), (612, 39), (605, 34),
                                (598, 39), (600, 31), (594, 26), (602, 26)))
        # 暂停与失焦是明确冻结状态，不能只依赖声音判断。
        if snapshot.is_paused:
            # 提示置于所有其他展示层之上。
            self._text(self._screen, "PAUSED - Esc resumes" if keyboard.is_focused else "FOCUS LOST - simulation frozen",
                       (355, 615), 30, (249, 222, 146), 500)
