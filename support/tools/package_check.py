# 临时目录隔离正式快照、构建结果与安装副本。
import tempfile
# 子进程全部采用参数列表，保留真实失败状态。
import subprocess
# 环境副本只控制测试显示，不改用户全局设置。
import os
# 安装验收使用调用方明确解释器。
import sys
# 复制正式测试进入安装验收目录，不挂载源码包。
import shutil
# 路径对象统一临时目录和产物定位。
from pathlib import Path
# Wheel内容必须核对制作区没有进入。
import zipfile
# 正式快照沿用精确路径允许集合。
from support.tools.export_game import copy_snapshot
# 离线依赖缓存仅来自当前环境的标准发行。
from support.tools.dependency_wheel import cache_installed_wheel
# wheel实际数据须与正式区域允许集合准确一致。
from support.tools.project_files import DATA_FILES

# 在无制作目录和源码包的安装环境验证模块、命令入口及正式机制回归。
def check_package(root: Path, build_python: str | None = None) -> list[str]:
    # 运行依赖和构建解释器可以独立指定，默认使用同一解释器。
    builder = build_python or sys.executable
    # 错误在此工具边界统一转换为可读结果。
    try:
        # 退出时清理临时快照，不修改原工作区源码。
        with tempfile.TemporaryDirectory(prefix="time-maze-package-") as directory:
            # 临时根不包含用户制作资料。
            base = Path(directory)
            # 正式源码快照与安装验收目录分开。
            source = base / "source"
            # 生成技术文件快照，未进行Git提交。
            names = copy_snapshot(root, source)
            # 提前拒绝任何制作路径。
            if any("production" in Path(name).parts for name in names):
                # 违反发行边界时停止构建。
                return ["干净快照包含制作目录"]
            # Wheel输出目录由临时构建拥有。
            wheels = base / "wheels"
            # 创建构建目录，不使用旧输出伪装本轮结果。
            wheels.mkdir()
            # 通过声明的setuptools后端构建，不联网安装隐式依赖。
            command = "from setuptools.build_meta import build_wheel; import sys; build_wheel(sys.argv[1])"
            # 缺少构建依赖时明确失败，调用者可指定已有构建解释器。
            subprocess.run([builder, "-c", command, str(wheels)], cwd=source, check=True, capture_output=True, text=True)
            # 只接受本轮生成的唯一游戏wheel。
            game_wheel = next(wheels.glob("vibe_time_maze-*.whl"))
            # 核对包内路径，不以构建成功代替范围审查。
            with zipfile.ZipFile(game_wheel) as archive:
                # 数据完整性直接检查本轮wheel，不只相信配置声明。
                actual_data = {name for name in archive.namelist() if name.startswith("time_maze/data/") and name.endswith(".json")}
                # 七区和清单、曲谱、文字缺一不可，多出的JSON同样拒绝。
                if actual_data != DATA_FILES:
                    # 保留旧产物，明确停止当前安装验收。
                    return [f"wheel运行数据不完整或越界: {sorted(actual_data ^ DATA_FILES)}"]
                # 正式安装包只包含time_maze与发行元数据。
                invalid = [name for name in archive.namelist()
                           # 辅助目录不得随wheel进入运行包。
                           if not (name.startswith("time_maze/") or ".dist-info/" in name)]
                # 不允许路径须终止安装验收。
                if invalid:
                    # 记录真实路径，便于修复打包配置。
                    return [f"wheel范围错误: {invalid}"]
            # pygame离线缓存从已验证的当前环境取得，不读取私人资产。
            dependency = cache_installed_wheel("pygame-ce", wheels)
            # 创建全新Python环境，避免依赖开发者site-packages。
            environment = base / "installed"
            # venv基于运行解释器建立，所有包稍后显式安装。
            subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True, capture_output=True)
            # 根据平台选择实际可执行文件路径。
            executable = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            # 离线安装本輪游戏与精确pygame依赖。
            subprocess.run([str(executable), "-m", "pip", "install", "--no-index", str(dependency), str(game_wheel)], check=True, capture_output=True)
            # 验收目录没有time_maze源码，导入必须来自已安装wheel。
            runtime = base / "runtime"
            # 正式测试独立复制，仍不含production或工具产物。
            shutil.copytree(source / "support/tests", runtime / "support/tests")
            # 工具边界回归需要正式工具副本，仍不复制游戏源码或制作目录。
            shutil.copytree(source / "support/tools", runtime / "support/tools")
            # 环境变量在子进程范围内设置虚拟显示和音频。
            variables = os.environ.copy()
            # 清除用户可能配置的源码搜索路径，防止误导入工作区。
            variables.pop("PYTHONPATH", None)
            # 离屏验证明确使用SDL虚拟显示，不伪称真实GUI。
            variables["SDL_VIDEODRIVER"] = "dummy"
            # 声音设备边界在虚拟设备中验证，听感仍独立。
            variables["SDL_AUDIODRIVER"] = "dummy"
            # 抑制pygame导入欢迎语，仅输出验证摘要。
            variables["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
            # 安装副本跑完整行为回归，不只短帧启动。
            subprocess.run([str(executable), "-m", "unittest", "discover", "-s", "support/tests"], cwd=runtime, env=variables, check=True)
            # 模块入口在安装目录外真实运行。
            subprocess.run([str(executable), "-m", "time_maze", "--silent", "--frames", "3"], cwd=runtime, env=variables, check=True, capture_output=True)
            # console入口与模块入口分别验证。
            console = environment / ("Scripts/time-maze.exe" if os.name == "nt" else "bin/time-maze")
            # 有限帧只作为启动证据，不代替上面的机制回归。
            subprocess.run([str(console), "--silent", "--frames", "3"], cwd=runtime, env=variables, check=True, capture_output=True)
            # 成功产物才复制到明确本机输出区。
            output = root / "support/tools/output"
            # 不发布、不上传，只保存wheel用于复现。
            output.mkdir(parents=True, exist_ok=True)
            # 本轮真实验证成功后替换同名产物。
            shutil.copyfile(game_wheel, output / game_wheel.name)
            # 报告验证边界与离线依赖来源。
            print(f"干净快照{len(names)}文件；离线wheel安装、正式回归、模块与console入口通过（SDL虚拟显示）")
    # 外部构建和安装失败需要保留真实stdout/stderr原因。
    except (subprocess.CalledProcessError, OSError, ValueError, StopIteration) as error:
        # 子进程输出有时为字节，统一转为可读文字。
        detail = getattr(error, "stderr", b"") or getattr(error, "stdout", b"") or str(error)
        # 不丢失pip或构建工具的失败原因。
        if isinstance(detail, bytes):
            # 诊断仅转换编码，不把失败当成功。
            detail = detail.decode("utf-8", errors="replace")
        # 非零结果由统一入口负责报告。
        return [f"干净包验收失败: {detail}"]
    # 空错误列表只表示本函数实际范围通过。
    return []
