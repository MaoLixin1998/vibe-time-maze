# 时间迷宫技术入口

更新：2026-10-10。状态：七区可玩灰盒v0.2.1已贯通，区域数据与专属规则／表现已按职责拆分。正式Python包使用pygame-ce实现2D俯视单人迷宫；完整路径、失败重试、昼夜／年龄、开箱和静音运行已回归验证。当前画面是基础几何占位，正式角色、美术、动画、听感与真人试玩另验。

## 技术文档

- [功能需求与验收](support/technical/requirements.md)：首版范围、状态规则与完成定义。
- [架构与接口](support/technical/architecture.md)：分层、单类文件、状态所有权与依赖边界。
- [灰盒公开API](support/technical/graybox-api.md)：当前模型及快照的实际契约。
- [Python / pygame补充](support/standards/python-pygame.md)：本项目语言规则、区域文件隔离、灰盒延续与检查覆盖；3.1条款已落实，可靠数据结构与资源集合由统一检查核验。
- [验证与发行](support/technical/packaging.md)：工作区、索引、干净包及GUI验收。
- [技术实施顺序](support/technical/roadmap.md)：先完整可玩流程、再画面完善的里程碑。
- [参考项目采纳记录](support/technical/reference-adoption.md)：两个参考项目的适用部分及不适用条款。
- [实际验收记录](support/technical/verification.md)：命令、版本、安装副本与真实窗口证据。

本机开发另读取通用规范1.6.1及项目AGENTS入口；通用正文及同版本纯技术项目副本经正文审阅允许纳入Git，本项目继续引用权威正文，不另行复制。本机混合AGENTS、总入口、Life Plan调度与制作资料继续排除，技术规范不作为游戏运行资源进入发行包。运行包为`time_maze`，正式默认资源由包内数据和基础绘制提供，不依赖开发者绝对路径或制作目录。

Git首次实现时已初始化，2026-10-09核对时为main分支、无提交、无已跟踪文件。当前首次技术提交与GitHub推送已授权，仅包含审阅后的代码、正式运行数据、测试、构建配置和纯技术文档；本机内容与产品发布继续按独立授权处理。

## 本机运行

当前本机独立环境为`.venv-game`，实际验证Python 3.13.13、pygame-ce 2.5.8：

```sh
.venv-game/bin/python -m time_maze
.venv-game/bin/python -m time_maze --silent
.venv-game/bin/python -m support.tools.check_project
.venv-game/bin/python -m support.tools.check_project --staged
.venv-game/bin/python -m support.tools.check_project --check-package --build-python python3
.venv-game/bin/python -m support.tools.export_game
```

操作：WASD／方向键移动，E交互，K打开三键乐器，1—7发一个音符，Shift＋数字高八度，Enter提交，Backspace清空，面板内Esc关闭、地图中Esc暂停／恢复，R失败重试，F5完整重开，Space跳过出口远景展开。打开乐器不暂停世界，右侧实时地图和鸡群状态保留危险反馈。

第一谱箱收录原创时间曲6-3-2-5-2-1，同一曲双向切换昼夜；第二谱箱为可选摇篮曲7-高2-6重复两遍。曲谱与三键组合在取得后可反复查阅。两箱位于迷宫两条长死胡同，默认地图提供目的地、地标与条件提示。当前时间曲与鸡回应为试玩候选。

新环境用Python 3.13建立venv，再用`python -m pip install -r requirements.lock`安装依赖。当前网络源未成功验证；本机离线验证从已安装正规pygame发行重建依赖wheel，缓存位于`support/tools/output/dependencies/`。独立构建后端在本机`python3`中可用，故检查命令显式选择`--build-python python3`；游戏运行与安装副本仍使用独立环境。

源码ZIP和wheel集中于`support/tools/output/`，均需要Python及声明依赖。wheel安装副本不含制作目录；macOS原生窗口另有cocoa启动和截图证据。没有交付包含解释器的原生.app，也未验证其他系统和主观音色。
