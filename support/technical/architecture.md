# 架构、接口与状态所有权

版本：1.2。更新：2026-10-10。正式灰盒v0.2.1已完成七区文件与专属规则／表现迁移，已实现结构见下图。功能与运行证据见[验收记录](verification.md)，正式角色、美术和最终音色另验。

箭头表示调用或导入依赖：入口 → 应用组装 → 输入／渲染／数据与声音适配／纯模型。输入调用模型公开能力；渲染只读快照；纯模型不导入pygame、IO或support。独立本机场景仅可单向调用主体。

```text
time_maze/
  __main__.py                         模块薄入口
  app/cli.py                         参数校验、启动错误转换
  app/application.py                 Application：循环、显示／声音生命周期
  app/game_factory.py                create_game：正式数据与依赖组装
  app/input_controller.py             InputController：焦点、按键、有界前缀
  model/game_session.py               GameSession：本局用例协调与完整重试
  model/player.py                     Player：位置与移动插值
  model/timeline.py                   Timeline：年龄、年份、唯一昼夜状态
  model/maze_state.py                 MazeState：共享箱子、占用门槛
  model/chicken_flock.py              ChickenFlock：分时代鸡群、警告与路径
  model/level_definition.py           LevelDefinition：整图只读定义
  model/room_definition.py            RoomDefinition：单区地板、门与地标
  model/portal_definition.py          PortalDefinition：方向、连接与条件
  model/interactive_object.py         InteractiveObject：独立物件及箱子终点
  model/rules_definition.py           RulesDefinition：曲谱与有限行为数值
  model/melody_definition.py          MelodyDefinition：音符、八度、效果
  model/game_snapshot.py              GameSnapshot：完整不可变查询值
  model/keyboard_snapshot.py          KeyboardSnapshot：输入展示值
  model/game_event.py                 GameEvent：单调序号的真实结果
  model/movement.py                   纯邻格、距离、鸡路径BFS
  model/keyboard_rules.py             严格音符校验与完整匹配
  model/transition_rules.py           通行与提示同源查询
  model/level_validation.py           正式数据纯内存校验
  model/area_rules/nest_entry.py      F孩童夜间安全入场条件
  model/area_rules/meadow_entry.py     G真正出口胜利条件
  adapters/content_loader.py          严格包资源JSON读取、交给纯校验
  adapters/area_loader.py             七区归属清单、组合资源边界
  adapters/audio_player.py            AudioPlayer与纯PCM合成、静音降级
  rendering/renderer.py               Renderer：基础世界、状态层、HUD、面板
  rendering/player_drawing.py         共用几何角色公开绘制
  rendering/areas/meadow_reveal.py     G出洞、站定、旷野展开
  rendering/resource_bundle.py        ResourceBundle：准备字体与地形缓存
  rendering/generated_resources.py    程序绘制静态底图与三键图示
  data/level.json                     七区清单v2、起点和全图配置
  data/areas/*.json                   下列七张独立区域布局v1
  data/{rules,text}.json              共享规则和文字，无拍摄时码
support/
  tests/                             正式回归、公开操作路径与状态图检查
  tools/check_project.py             工作区／索引／干净包入口
  tools/area_structure_check.py       实际工作区／索引资源与构建集合校验
  tools/project_files.py              精确技术路径允许集合
  tools/dependency_wheel.py           离线复用已安装正规依赖发行
  tools/export_game.py                允许集合快照与源码ZIP
  tools/package_check.py              无制作目录的wheel安装验收
  technical/、standards/              纯技术说明与项目补充
  production/                        仅本机制作资料、旧稿和显式拍摄
```

每个类独立文件，无年龄继承树。GameSession组合Player、Timeline、MazeState和ChickenFlock，协调move、interact、play_keyboard、update、retry、restart；实际字段与签名见[灰盒API](graybox-api.md)。构造显式注入已校验关卡与规则。模型导入不读数据、不启动设备，应用工厂才加载正式包资源。

## 已实现的区域文件隔离

强制边界见[Python补充3.1](../standards/python-pygame.md#31-区域文件隔离与共享机制强制)。每区数据单独维护，通用机制保持共享，独有业务和表现分别归入原有层，不建立七套游戏循环。

以下为当前已实现文件；仅F、G存在专属入场规则，其他区域由数据与共用机制完成：

```text
time_maze/
  data/level.json                     区域清单、起点与必要全图配置
  data/areas/a_sword_chamber.json      A布局、碰撞、连接和物件
  data/areas/b_maze_crossroads.json    B布局、连接和两谱箱
  data/areas/c_cargo_corridor.json     C布局、货箱与连接
  data/areas/d_night_gate.json         D布局、夜闸与连接
  data/areas/e_chicken_yard.json       E布局、领地、地标与排水连接
  data/areas/f_nest_passage.json       F布局、巢、出口与连接
  data/areas/g_meadow.json             G布局、奖励箱与资源引用
  model/area_rules/nest_entry.py      F检查点条件
  model/area_rules/meadow_entry.py     G胜利入场条件
  rendering/areas/meadow_reveal.py     G出口展开的专属表现模块
  model/、app/、adapters/              原有共享规则、输入和装载能力
```

装载器→区域清单／独立区域文件→既有只读LevelDefinition→GameSession与Renderer，箭头表示装载／调用；GameSession→区域规则并传入所需公开数据／能力，区域规则不反向导入GameSession；Renderer→区域专属表现，后者只读快照、不持有输入控制器。GameSession继续持有一局状态与完整恢复协调，区域文件分离不建立互相独立的七份进度。

清单采用schema_version=2，每项仅有id和file，文件归属由area_loader.AREA_FILES准确声明；各区文件schema_version=1，只有room布局对象。assemble_level拒绝缺区、重复、错配、越界路径及清单内嵌rooms，组合成原有parse_level的v1内存输入，整体校验全部连接。load_content返回契约、LevelDefinition和完整快照保持不变。没有并列维护第二份当前布局。

Renderer调用draw_meadow_reveal(surface,snapshot,resources)，专属表现使用共用draw_player；两者不推进状态。夜色按房间领地数据决定，英文区域名从正式文字映射读取，公共渲染器不再内嵌七区名称分支。GameSession调用两个区域纯查询，仍负责跨区提交、胜利、事件和完整检查点。

统一检查消费实际工作区／索引blob，核验七区来源、ID、引用、全图拓扑、精确package-data和Git资源例外；不执行索引源码。空索引不代表结构验收。模块职责、通用机制复用、注释语义仍人工审阅，不宣称自动判断所有区域ID分支。

状态阶段为intro、exploring、sliding、pushing、failed、exit_reveal和reward。初次拔剑只变成年并保存A安全快照，玩家跨滑落口才进入A→B过场。货箱从C南侧推到C内北凹位，过程中位置插值，完成后开通A↔C；箱子跨年龄／昼夜共享。鸡群位置、警告与计时分时代持有，年龄变化不继承另一时代仇恨。

B第一谱箱收录time_shift，effect=toggle_day。同一原创候选6-3-2-5-2-1切换白天／夜晚。第二谱箱收录egg_lullaby，音符为7-高2-6重复两遍，effect=egg_lullaby，仅反馈，不改变世界。鸡回应3-5-3-2为可替换试玩候选；其他五首隐藏曲准确输入与效果仍待定。曲谱展示和匹配同源，收录只控制显示，不增加施法拥有条件。Enter提交完整序列，最大12音，不限节奏；未完成、错音或错八度不改世界。

InputController拥有面板、按键和前缀，过滤自动重复；关闭面板、暂停、失焦、失败、重试与重开清空。面板不暂停世界，面板方向键不移动；面板内Esc只关闭并清空输入，地图中Esc才暂停／恢复。应用把模型与输入不可变快照传入Renderer；渲染不持有输入控制器、不推进状态。音符只播放一个合成笛音，事件按sequence只消费一次；重试与重开不回滚事件号。

邻近提示与通行条件共同调用portal_access。门槛占用时切白天保留当前落脚，离开后关闭；不弹出玩家。每区共用静态地形，箱、剑、谱箱、鸡、门、年份独立展示，昼夜不复制整图，主要光照变化在E。当前字符为通用几何占位，不冒称正式vibe角色。必要操作和条件有随pygame分发字体可读的英文fallback，中文系统字体只作增强。

F合法孩童夜间安全入场保存实际坐标的完整快照，包含箱、谱箱、收录及两时代鸡状态。失败只通过retry整体恢复，完整重开回初始定义。真正跨F→G才胜利和结束追逐，先有限exit_reveal过场，结束或跳过后reward允许移动；玩家邻近交互才能一次领奖。暂停冻结进度，跳过不发奖。

默认只加载包内JSON和程序绘制资源，不探测制作资料。尚未需要外部增强素材清单，未来新增时再展示依赖与验证。主体、wheel和正式回归始终不导入support.production；源码ZIP按精确技术允许集合生成。工作区与安装副本、SDL虚拟显示与真实GUI、声音设备与主观听感分别记录。
