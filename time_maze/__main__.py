# 模块入口复用唯一CLI，不重复创建应用循环。
from time_maze.app.cli import main

# 只有显式模块运行才启动窗口，普通导入保持无副作用。
if __name__ == "__main__":
    # 保留CLI和设备边界的真实退出状态。
    raise SystemExit(main())
