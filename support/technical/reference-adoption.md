# 参考项目采纳记录

更新：2026-10-09。只读参考两个项目的现行技术文档；本作设计由本作需求决定，不复制游戏实现或私人制作内容。正式游戏主线旋律由本作原创，新增少量选定参考曲段的隐藏彩蛋需求，六首曲名已选定，摇篮曲短句已实现，其余输入与回应待定；三键七音试听与完整游戏实现分别记录。

| 来源 | 本作采用 | 不继承 |
| --- | --- | --- |
| hero-clock-out/TECHNICAL.md、support/standards/python-pygame.md（1.3） | Python/pygame分工、纯模型、应用装配、资源显式注入、support辅助根 | 追逐游戏具体规则、旧入口兼容文件、其已完成状态与依赖版本 |
| hero-clock-out/support/technical/architecture.md | 模型不反向依赖界面、单类文件、只读绘图、正式数据单一来源 | 史莱姆、开场阶段、原游戏地图与显示参数 |
| hero-clock-out/support/technical/packaging.md、support/tools/check_project.py | 工作区/真实索引/干净包分开报告、允许清单构建、基础资源可运行 | 提交授权、该项目hook、未适配的路径和参数 |
| vibe-pet/docs/08_代码规范.md（2.4） | Python命名、类型、状态封装、中文上方说明、检查覆盖的实际边界 | PyObjC选择器、NSPanel/NSView、Objective-C入口、macOS26限制 |
| vibe-pet/docs/04_详细需求文档.md、docs/07_下一版画面设置与代码结构评估.md | 已确认/候选/实现/验收分开记录，需求与现状分开 | 桌宠16动作、24帧、Agent、桌面权限及Sources目录模板 |

参考项目为同机hero-clock-out与vibe-pet，本作运行不依赖其路径。vibe-pet当前上层入口为0.3.1，部分需求/评估仍保留0.3.0和旧单文件描述；不把历史状态当现状。部分旧链接指向hero的旧docs/assets目录，本作重新建立现行路径。

本作拍摄场景采用`support/production/scenes/`，无需照搬hero放在正式测试子区的路径例外。正式测试明确只发现`support/tests/`；support不作为整体Git或发行允许项。Git在首次实现时初始化且无提交／已跟踪文件；未安装hook，来源项目未修改。

本作已有`support/production/scenes/keyboard_demo/`独立试听，七种非空三键组合对应do至si，每个组合只播放一个笛子音色单音；Shift＋数字为高八度。该demo只试听音符，不含原作旋律触发或正式游戏效果；不是来自参考项目的已完成功能，也不是正式运行包的依赖。未来正式曲谱按1—7音符ID及octave事件独立设计，正式灰盒用Enter完整提交、最多12音，不沿用旧固定三音方案。
