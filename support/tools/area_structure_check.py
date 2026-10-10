# 精确文件集合由正式允许边界提供，不整体放行区域目录。
from support.tools.project_files import DATA_FILES
# 清单组合只接收文本数据，不执行被检查版本的源码。
from time_maze.adapters.area_loader import assemble_level
# 严格JSON解析和纯模型拓扑校验与正式加载同源。
from time_maze.adapters.content_loader import decode_json
# 完整七区必须一起校验目标、落脚与物件引用。
from time_maze.model.level_validation import parse_level, parse_rules
# TOML构建配置属于数据，不作为Python执行。
import tomllib
# 输入允许只读映射，工具不改写工作区或索引。
from collections.abc import Mapping

# 检查工作区或索引的实际blob集合；两者由入口分别显式取得。
def check_area_structure(blobs: Mapping[str, bytes]) -> list[str]:
    # 构建和Git边界也须包含全部准确区域文件。
    required = DATA_FILES | {"pyproject.toml", ".gitignore"}
    # 区域目录中多出的布局可能成为第二份现行来源。
    extra = {name for name in blobs if name.startswith("time_maze/data/") and name.endswith(".json")} - DATA_FILES
    # 缺资源和额外布局分别报告，不吞掉后续错误。
    errors = [f"区域结构缺少文件: {name}" for name in sorted(required - blobs.keys())]
    # 未声明JSON不能借目录名成为正式资源。
    errors.extend(f"区域结构存在未声明JSON: {name}" for name in sorted(extra))
    # 必要输入不完整时不尝试伪造默认布局。
    if errors:
        # 准确返回文件级失败。
        return errors
    # 所有格式和拓扑错误在检查边界统一转成可读诊断。
    try:
        # 读取函数只访问传入blob，不隐式取工作区替代索引。
        def read_resource(name: str) -> object:
            # UTF-8、重复字段和非有限常量均经过正式解析。
            return decode_json(blobs[f"time_maze/data/{name}"].decode("utf-8"))
        # 曲谱引用与正式加载完全同源。
        rules = parse_rules(read_resource("rules.json"))
        # 所有独立区域一起检查跨区落脚与连接。
        parse_level(assemble_level(read_resource("level.json"), read_resource), rules)
        # 构建声明必须准确列出同一批JSON，不能使用宽泛通配。
        configuration = tomllib.loads(blobs["pyproject.toml"].decode("utf-8"))
        # 提取声明的正式包资源集合。
        declared = configuration["tool"]["setuptools"]["package-data"]["time_maze"]
        # 只接受无重复的精确相对路径数组。
        if type(declared) is not list or len(declared) != len(DATA_FILES) or set(declared) != {name.removeprefix("time_maze/") for name in DATA_FILES}:
            # 防止源码可玩但安装后缺区。
            errors.append("package-data与正式区域资源集合不一致")
        # Git忽略规则必须逐项开放数据，不把整个素材目录放行。
        ignore_lines = blobs[".gitignore"].decode("utf-8").splitlines()
        # 查明每一个正式数据文件都有精确例外。
        if any(f"!/{name}" not in ignore_lines for name in DATA_FILES):
            # 实际Git匹配和正文仍另行审阅。
            errors.append(".gitignore缺少准确运行资源例外")
    # 数据错误不能被当成检查器成功。
    except (ValueError, UnicodeError, KeyError, TypeError) as error:
        # 报告真实原因，不修改文件。
        errors.append(f"区域结构／拓扑无效: {error}")
    # 只覆盖可靠数据条款，职责和注释语义仍人工审阅。
    return errors
