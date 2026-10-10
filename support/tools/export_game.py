# 正式快照只从已声明的技术目录读取文件。
from pathlib import Path
# 临时目录保护已有可用产物。
import tempfile
# 文件复制不使用shell展开。
import shutil
# 源码ZIP是可检查的标准归档。
import zipfile
# 所有导出路径与索引共用同一允许集合。
from support.tools.project_files import is_allowed_path

# 枚举正式技术文件，制作区和虚拟环境不参与递归。
def collect_files(root: Path) -> tuple[Path, ...]:
    # 根入口仅在明确存在时纳入。
    files = [root / name for name in (".gitignore", "TECHNICAL.md", "main.py", "pyproject.toml", "requirements.lock")
             # 无效文件不会混入快照。
             if (root / name).is_file() and not (root / name).is_symlink()]
    # 主体、正式测试、工具和纯技术资料分别枚举。
    for folder in ("time_maze", "support/tests", "support/tools", "support/standards", "support/technical"):
        # 不递归到辅助根下的制作资料。
        for path in (root / folder).rglob("*"):
            # 只处理正式普通文件，符号链接不作为发行输入。
            if path.is_file() and not path.is_symlink() and is_allowed_path(path.relative_to(root).as_posix()):
                # 输出、缓存和私人资料不在允许集合。
                files.append(path)
    # 排序后的不可变列表便于检查和复现。
    return tuple(sorted(set(files)))

# 将正式文件复制至显式临时快照，不挂载制作目录。
def copy_snapshot(root: Path, destination: Path) -> tuple[str, ...]:
    # 记录准确复制范围供验证报告。
    names = []
    # 每个文件都经过相同路径集合筛选。
    for source in collect_files(root):
        # 相对路径保留运行和测试模块结构。
        relative = source.relative_to(root)
        # 创建实际需要的父目录。
        (destination / relative).parent.mkdir(parents=True, exist_ok=True)
        # 只复制源文件，不复制开发者文件属性。
        shutil.copyfile(source, destination / relative)
        # 以标准分隔符记录到清单。
        names.append(relative.as_posix())
    # 返回正式快照的准确路径集合。
    return tuple(names)

# 显式源码导出使用临时文件，成功后再替换旧ZIP。
def export_source(root: Path, output_directory: Path) -> Path:
    # 输出集中到仅本机的技术产物区。
    output_directory.mkdir(parents=True, exist_ok=True)
    # 固定名称表达灰盒阶段，不冒充独立原生程序。
    target = output_directory / "time-maze-graybox-source.zip"
    # 临时构建失败时已有产物保持可用。
    with tempfile.TemporaryDirectory(prefix="time-maze-source-") as directory:
        # 临时ZIP不含制作内容。
        temporary = Path(directory) / target.name
        # 用明确文件清单创建归档。
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            # 不压缩整个工作区。
            for path in collect_files(root):
                # 写入干净相对路径。
                archive.write(path, path.relative_to(root).as_posix())
        # 完成后才替换已存在的源码归档。
        shutil.copyfile(temporary, target)
    # 返回实际创建的本机产物。
    return target

# 只有显式运行导出命令才写ZIP。
if __name__ == "__main__":
    # 工具位置决定项目根，支持从其他目录调用。
    root_directory = Path(__file__).resolve().parents[2]
    # 打印实际产物路径，不声称已安装或发布。
    print(export_source(root_directory, root_directory / "support/tools/output"))
