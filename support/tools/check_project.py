# 使用语法树检查源码的可靠形式，不把自动通过当成人工语义验收。
import ast
# 用命令行参数区分工作区、索引和干净安装包检查。
import argparse
# 用路径对象把检查范围固定在当前项目。
from pathlib import Path
# 用正则核对说明中是否包含中文。
import re
# Git和正式测试通过参数列表运行，不拼接可执行命令。
import subprocess
# 子命令继续使用当前明确选择的解释器。
import sys

# 索引与构建共用正式路径允许集合。
from support.tools.project_files import is_allowed_path
# 区域结构检查消费实际工作区或索引的文本blob。
from support.tools.area_structure_check import check_area_structure

# 检查单个Python源码的编码、语法、单类文件和中文上方说明。
def check_source(relative_path: str, content: bytes) -> list[str]:
    # 每个文件返回独立错误，便于定位而不吞掉其他失败。
    errors = []
    # 编码和语法错误在文件边界转换为明确诊断。
    try:
        # 按项目规定解码UTF-8，不容忍静默替换。
        source = content.decode("utf-8")
        # 只解析文本，不执行被检查源码。
        tree = ast.parse(source, filename=relative_path)
    # 拒绝非法编码和语法。
    except (UnicodeError, SyntaxError) as error:
        # 保留原始原因供修复。
        return [f"{relative_path}: {error}"]
    # 末尾换行便于差异与工具一致处理。
    if content and not content.endswith(b"\n"):
        # 记录规则而不自动改写文件。
        errors.append(f"{relative_path}: 缺少末尾换行")
    # 一个源文件只容纳一个类，数据类与测试类同样适用。
    if sum(isinstance(node, ast.ClassDef) for node in ast.walk(tree)) > 1:
        # 类职责和文件归属仍另作人工审阅。
        errors.append(f"{relative_path}: G04 单类单文件")
    # 行表用于检查逻辑语句正上方的独立说明。
    lines = source.splitlines()
    # 检查各层语句，不只检查函数入口。
    for node in ast.walk(tree):
        # 纯文本常量不是逻辑语句说明目标。
        if not isinstance(node, ast.stmt) or isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            # 跳过无需逐句注释的语法项。
            continue
        # 装饰器属于定义之前，整体说明放在组之前。
        line_number = min([node.lineno] + [item.lineno for item in getattr(node, "decorator_list", [])])
        # 取逻辑行的直接上方，不从远处找一条通用说明。
        previous = lines[line_number - 2].strip() if line_number > 1 else ""
        # 中文说明须独立注释，不能以行尾注释替代。
        if not previous.startswith("#") or not re.search(r"[\u4e00-\u9fff]", previous):
            # 给出真实一基行号。
            errors.append(f"{relative_path}:{line_number}: G01 缺少中文上方说明")
        # 核心模型不能倒向设备、磁盘或制作区。
        if relative_path.startswith("time_maze/model/") and isinstance(node, (ast.Import, ast.ImportFrom)):
            # 两种导入形式统一为模块名列表。
            modules = [item.name for item in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            # 本次纯模型允许标准纯计算库，不允许pygame或辅助目录。
            if any(module.split(".")[0] in {"pygame", "support", "pathlib", "os", "json"} for module in modules):
                # 报告依赖方向错误。
                errors.append(f"{relative_path}:{node.lineno}: 纯模型依赖越界")
    # 返回全部可机械判断的问题。
    return errors

# 显式执行检查，工作区检查不会被报告成索引或远程CI验收。
def main() -> int:
    # 统一入口只解析本项目命令。
    parser = argparse.ArgumentParser(description="时间迷宫：工作区/索引/干净包检查")
    # 索引模式只读Git blob。
    mode = parser.add_mutually_exclusive_group()
    # 同一次运行只选择索引检查或干净包检查，避免参数被静默忽略。
    mode.add_argument("--staged", action="store_true")
    # 干净包验收由独立正式工具负责。
    mode.add_argument("--check-package", action="store_true")
    # 离线构建可选择具备声明后端的独立解释器，运行验证仍使用当前解释器。
    parser.add_argument("--build-python")
    # 使用用户实际传入的选项。
    options = parser.parse_args()
    # 根据工具文件位置确定项目根，避免依赖当前目录。
    root = Path(__file__).resolve().parents[2]
    # 每项失败都累计，最后以非零状态退出。
    errors = []
    # 索引不运行其中的任意源码。
    if options.staged:
        # 未合并索引没有可审查的唯一源码版本，先明确拒绝冲突。
        conflicts = subprocess.run(["git", "ls-files", "--unmerged", "-z"], cwd=root, capture_output=True, check=True)
        # 不尝试执行或拼接冲突阶段的源码。
        if conflicts.stdout:
            # 返回明确失败而不修改真实索引。
            print("真实索引存在未解决冲突，不能验收", file=sys.stderr)
            # 冲突必须由实际合并处理，不能跳过检查。
            return 1
        # -z保留含空格的真实路径，ls-files列出整个索引。
        result = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True)
        # UTF-8路径与零字节分割不经过shell展开。
        paths = [path for path in result.stdout.decode("utf-8").split("\0") if path]
        # 仅收集索引实际数据，结构检查不得偷读工作区替代缺失资源。
        blobs = {}
        # 审核每个真实索引blob。
        for path in paths:
            # 所有blob都只读索引，不运行其中的代码。
            blob = subprocess.run(["git", "show", f":{path}"], cwd=root, capture_output=True, check=True).stdout
            # 同一索引集合供后续数据结构检查。
            blobs[path] = blob
            # 不允许的路径直接报错。
            if not is_allowed_path(path):
                # 不自动移除索引或修改Git。
                errors.append(f"索引禁止路径: {path}")
            # Python只读解析索引版本。
            elif path.endswith(".py"):
                # 累加当前blob诊断。
                errors.extend(check_source(path, blob))
        # 空索引只报告范围，有内容时必须包含完整可构建资源。
        if paths:
            # 检查工具来自当前可信入口，只解析实际索引配置和布局。
            errors.extend(check_area_structure(blobs))
        # 明确空索引没有源码验收结论。
        print(f"真实索引：{len(paths)} 个路径；未执行索引源码")
    # 工作区只检查明确正式源码。
    else:
        # 主体与辅助代码分别选取，不发现production测试。
        paths = [path for folder in ("time_maze", "support/tests", "support/tools")
                 for path in (root / folder).rglob("*.py") if "__pycache__" not in path.parts]
        # 根源码入口在存在时另列。
        if (root / "main.py").exists():
            # 不把根目录递归扫描为正式源码。
            paths.append(root / "main.py")
        # 按文件执行形式检查。
        for path in paths:
            # 相对路径用于易读诊断。
            errors.extend(check_source(path.relative_to(root).as_posix(), path.read_bytes()))
        # 读取全部运行JSON以发现遗漏或多出的第二布局，不读取制作区。
        resources = list((root / "time_maze/data").rglob("*.json"))
        # 构建与忽略文件作为数据一并核验。
        resources.extend(root / name for name in ("pyproject.toml", ".gitignore") if (root / name).exists())
        # 每项内容只来自当前工作区，与索引模式分开报告。
        blobs = {path.relative_to(root).as_posix(): path.read_bytes() for path in resources}
        # 结构失败会阻止回归和打包被误报成功。
        errors.extend(check_area_structure(blobs))
        # 只在正式测试存在时运行明确发现范围。
        if (root / "support/tests").exists() and not errors:
            # unittest的失败返回码保留到统一入口。
            result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "support/tests"], cwd=root)
            # 失败不能继续声称工作区通过。
            if result.returncode:
                # 用统一诊断保留测试状态。
                errors.append("正式回归失败")
        # 独立构建检查仅由显式参数触发。
        if options.check_package and not errors:
            # 模块导入保持在显式工具边界，主体不会导入本工具。
            from support.tools.package_check import check_package
            # 返回真实干净快照验收结果。
            errors.extend(check_package(root, options.build_python))
        # 输出真实工作区范围。
        print(f"工作区形式检查：{len(paths)} 个Python文件")
    # 逐项展示原因，不隐藏细节。
    for error in errors:
        # 每条诊断单独成行。
        print(error, file=sys.stderr)
    # 零值只表示本入口实际执行范围成功。
    return int(bool(errors))

# 命令行运行才启动检查，普通导入不产生副作用。
if __name__ == "__main__":
    # 保留失败退出状态给shell和未来CI。
    raise SystemExit(main())
