# 项目阶段与范围补充

版本：0.8。更新：2026-10-10。适用：本项目Python源码、正式运行数据、测试、构建工具和技术文档；叠加通用开发规范1.6.1。

## 当前技术阶段

Python与pygame-ce构建单人离线2D俯视迷宫。正式灰盒v0.2.1已贯通七区，使用程序绘制基础资源；角色、美术、最终音色及无指导真人试玩仍待验收。状态所有权、公开接口与依赖方向见[架构](../technical/architecture.md)，实际命令及证据见[验收记录](../technical/verification.md)。

首次实现或改变结构前展示R02分层、包树、文件职责与公开边界。沿用正式灰盒核心继续开发；占位替换不能代替操作空间、动画、公平性与完整试玩验收。候选需求、已实现功能和已验证结论分别记录。

主线时间曲time_shift的effect为toggle_day，当前候选6-3-2-5-2-1；Enter提交、不限节奏，最终听感待试玩。B第二谱箱为可选egg_lullaby，输入7-高2-6重复两遍，仅反馈不改世界，不作为通关依赖；两谱真实开箱取得并跨年龄／昼夜保留。其余隐藏旋律的输入和效果待逐项确定。

## 目录与依赖

- time_maze/：正式运行包；app组装与输入，model纯业务，adapters数据与声音，rendering只读绘制，data正式配置与七区布局。
- support/tests/、support/tools/：明确发现的正式测试与技术工具，不是运行包依赖。
- support/technical/、support/standards/：纯技术正文；根TECHNICAL.md为技术入口。
- support/production/：仅本机内容、增强素材、独立场景与历史归档；排除主体依赖、默认测试、Git与发行。

support是辅助组织容器，不整体开放Git或发行。根README.md、AGENTS.md和其他混合本机入口不纳入仓库。普通资料目录不建立无用途Python包；主体不导入support或探测本机内容。

## 区域职责与唯一来源

A—G各有独立JSON；level.json仅存v2区域清单、起点与全图配置。F／G专属入场规则在model/area_rules，G旷野展开在rendering/areas；通用机制共用，不建立七套循环。load_content组合后整体校验ID、引用、通行条件和合法落脚；完整单局状态与重试仍由GameSession协调。

结构迁移同步装载、资源定位、默认测试、精确Git／打包集合和文档。旧稿仅本机归档，当前布局不并列维护两份。规则细节见[Python补充3.1](python-pygame.md#31-区域文件隔离与共享机制强制)。

## 检查与Git边界

统一入口python -m support.tools.check_project；工作区、真实索引、干净wheel安装副本、GUI和听感分别报告。索引检查只读取实际blob、不执行索引源码；CI如配置须检查实际检出版本。目前未安装Git hook或CI，不更改全局core.hooksPath。

代码、正式运行JSON、测试、构建配置及纯技术文档按准确允许集合和实际正文审阅。混合记录、私人路径、原照、增强素材及生成产物仍默认排除。首次技术提交与GitHub推送已获授权；此授权不扩大到本机内容、其他项目或产品发布，后续上传仍按明确任务范围处理。
