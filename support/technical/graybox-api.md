# 灰盒公开接口

版本：0.3，2026-10-10。以下接口已落实到正式包；地图尺寸、最终曲谱、鸡速与演奏公平性仍待真人试玩核定。

`time_maze.adapters.content_loader.load_content()` 返回 `(level, rules, text_mapping)`；第三项为只读映射。`GameSession(level, rules)` 创建独立游戏，不启动设备或读取文件。

- `move(direction: str) -> bool`：方向为 `up/down/left/right`，仅接受合法完整格移动。先站到门槛，再沿门方向跨区；一次移动期间拒绝新移动。
- `interact() -> str`：邻近物件交互、成年推箱、剑台切龄或G领奖；返回稳定结果ID。
- `play_keyboard(note_events: tuple[tuple[int, int], ...]) -> str`：音符1—7、八度0/1，最多12音，完整提交；失败无世界副作用。
- `update(seconds: float)`：有限非负秒，内部最大0.05秒子步，最多追赶0.25秒。
- `set_paused(bool)`、`retry() -> bool`（只在failed）、`restart()`、`skip_cutscene()`。
- `snapshot() -> GameSnapshot`：不可变嵌套快照；`level`、`rules`为只读属性。

`GameSnapshot` 字段：`region, pos, visual_pos, age, year, is_day, phase, is_paused, is_won, reward_claimed, box_open, box_progress, collected_scores, opened_chests, chickens, chicken_state, events, message, nearby_hint, cutscene_progress, box_region, box_visual_pos, held_thresholds`。`chickens` 为当前时代的 `(region, x, y, mode)` 元组；`chicken_state` 包含两个时代不可变恢复值。phase为 `intro/exploring/sliding/pushing/exit_reveal/reward/failed`。`GameEvent(sequence, kind, detail='')` 序号不随retry/restart回滚；事件历史最多64项，消费者按sequence去重。

地图：`LevelDefinition.rooms` 为 `RoomDefinition` 元组；`.room(id)` 查询；`chicken_spawns` 为按巢顺序的 `(region,x,y)` 元组。Room有 `id,name,width,height,floors,portals,objects,territory,landmarks,pedestal_steps`；`floors/territory`为坐标frozenset，`pedestal_steps`为三层静态矩形 `(x1,y1,x2,y2)` 元组。Portal有 `id,position,direction,target_region,target_position,condition,label,kind`；condition为 `open/child/cargo/night/child_day`。Object有 `id,kind,position,payload,target_position`，最后一项仅货箱使用。Landmark为 `(x,y,label)`。房间统一坐标从左上开始，y向下。

规则：`RulesDefinition.melodies` 为 `MelodyDefinition` 元组，另有 `movement_seconds,warning_seconds,chicken_step_seconds,return_step_seconds,exit_seconds,max_notes,box_seconds,slide_seconds`。Melody有 `id,name,notes,effect,category`；展示按 `collected_scores` 筛选。时间曲ID为 `time_shift`，effect为 `toggle_day`；摇篮曲ID/effect为 `egg_lullaby`；鸡回应为 `chicken_call`。事件至少有 `age_changed,day_changed,score_collected,box_started,box_opened,chicken_warning,chicken_call,egg_lullaby,failed,retried,restarted,won,reward_claimed,cutscene_finished,checkpoint_saved,slide_started,slide_finished`。

`transition_rules.portal_access(portal,age,is_day,box_open,is_held=False)` 返回 `(allowed,reason)`。渲染延迟关闭夜门时传入 `(snapshot.region,portal.position) in snapshot.held_thresholds`，与真实通行同源。白天占用门显示“占用中，离开后关闭”，占用者从任一侧离开后才关闭，不弹出玩家。

首次剑台拔剑保存A实际安全格；孩童夜间实际入F时保存入口合法格及完整两时代鸡群、货箱、谱箱和收录状态。重试恢复检查点，不改变声音序号。推箱要求成年站在箱南一格，朝北按E；可先向上顶箱以转身。出口8秒过场可跳过，正常结束与跳过保持同一G入口合法格、未领取状态。

包资源加载与直接 `GameSession(level,rules)` 构造均复用纯数据校验，拒绝可变嵌套、bool伪整数、无效ID/引用、非有限数值、重复字段及曲谱前缀歧义。基础规则、地形及文字不读取本机制作区。

磁盘布局：data/level.json为v2清单，areas数组每项为id/file，另有initial_region、initial_position与chicken_spawns；data/areas下七个准确文件分别为v1的schema_version/room包装。磁盘格式与冻结模型独立，assemble_level(manifest,read_resource)生成既有parse_level的v1输入。decode_json(content)严格拒绝重复字段和非有限常量。load_content返回契约及模型公开接口不变。

区域纯规则is_safe_nest_entry(region,age,is_day)、is_meadow_exit(portal)只返回条件结果；完整状态仍由GameSession持有。draw_player(surface,center,age,cell_pixels)与draw_meadow_reveal(surface,snapshot,resources)只绘制，不持有输入或改写世界。

地图和规则不可被UI改写。正文只含技术接口，视频演出台词留制作区。
