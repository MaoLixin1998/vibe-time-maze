# 不可变数据类让渲染读取输入展示值而不访问控制器状态。
from dataclasses import dataclass

# 面板快照仅包含独立值，不持有可变按键或音符列表。
# 冻结数据类禁止字段重赋值，嵌套容器另按模型边界核验。
@dataclass(frozen=True)
class KeyboardSnapshot:
    # 面板打开时输入音符而不移动玩家，世界仍然运行。
    is_open: bool
    # 当前有界前缀，每个音由数字和八度构成。
    notes: tuple[tuple[int, int], ...]
    # 最近单音用于展示三键组合，空值表示尚未演奏。
    last_note: tuple[int, int] | None
    # 最近单音距今秒数只影响涟漪表现。
    last_note_seconds: float
    # 焦点丢失时界面展示冻结原因。
    is_focused: bool
    # 输入长度等本地反馈不改变游戏业务状态。
    feedback: str
