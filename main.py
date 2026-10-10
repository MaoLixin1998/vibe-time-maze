# 源码薄入口复用正式包CLI，安装后入口保持同一行为。
from time_maze.app.cli import main

# 普通导入不启动游戏或读取正式数据。
if __name__ == "__main__":
    # 明确运行时才创建当前应用，并保留失败退出状态。
    raise SystemExit(main())
