# 路径允许集合只描述本项目正式技术范围。
from pathlib import Path
# 正式资源归属由装载边界统一声明，工具只单向引用。
from time_maze.adapters.area_loader import AREA_FILES

# 技术根文件逐项允许，不整体开放本机协作入口。
ROOT_FILES = frozenset({".gitignore", "TECHNICAL.md", "main.py", "pyproject.toml",
                        "requirements.lock"})
# 技术资料逐项放行，与.gitignore同步，不按目录和后缀整体导出。
DOCUMENT_FILES = frozenset({
    # 当前技术入口均不含视频创作或私人资料。
    "support/technical/requirements.md", "support/technical/architecture.md",
    # 构建边界与当前里程碑分别维护。
    "support/technical/packaging.md", "support/technical/roadmap.md",
    # 参考采纳记录只保留技术选择。
    "support/technical/reference-adoption.md", "support/technical/graybox-api.md",
    # 实际验收明确命令、版本和未覆盖范围。
    "support/technical/verification.md",
    # 项目补充与纯技术通用规范副本仍须审阅正文。
    "support/standards/project-scope.md", "support/standards/python-pygame.md",
    # 允许同版本技术副本不表示自动复制或提交。
    "support/standards/general-coding-standard.md",
})
# 运行JSON逐项允许，不整体开放areas目录中的未知资源。
DATA_FILES = frozenset({"time_maze/data/level.json", "time_maze/data/rules.json", "time_maze/data/text.json"}
                       # 区域文件与正式装载器共用稳定资源归属。
                       | {f"time_maze/data/{name}" for _, name in AREA_FILES})

# 判断一个相对路径是否属于正式技术范围；制作资料始终拒绝。
def is_allowed_path(relative_path: str) -> bool:
    # 将平台分隔符统一为可审查的相对路径。
    path = Path(relative_path)
    # 拒绝绝对路径和父目录逃逸，允许集合只接收规范相对路径。
    if path.is_absolute() or ".." in path.parts:
        # 不用路径规范化掩盖不可信输入。
        return False
    # 根目录只开放明确文件。
    if relative_path in ROOT_FILES or relative_path in DOCUMENT_FILES:
        # 返回准确允许结果。
        return True
    # 主体只允许Python和明确运行JSON。
    if path.parts[:1] == ("time_maze",):
        # 数据文件不能因为目录存在而整体放行。
        return path.suffix == ".py" and "__pycache__" not in path.parts or relative_path in DATA_FILES
    # 正式辅助代码与技术文档分别限定后缀。
    if len(path.parts) >= 3 and path.parts[0] == "support":
        # 测试与工具仅允许源文件，拒绝输出目录。
        if path.parts[1] in {"tests", "tools"}:
            # 防止缓存或构建输出被纳入允许集合。
            return path.suffix == ".py" and "output" not in path.parts and "__pycache__" not in path.parts
        # 技术资料只由上方明确文件集合放行，其他新稿默认拒绝。
        return False
    # 其余路径不属于本次正式集合。
    return False
