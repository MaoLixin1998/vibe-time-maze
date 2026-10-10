# 结果事件采用不可变值，由会话维护发送序号。
from dataclasses import dataclass

# 同一序号只表示一次真实发生的业务结果。
# 冻结数据类禁止字段重赋值，嵌套容器另按模型边界核验。
@dataclass(frozen=True)
class GameEvent:
    # 序号在retry和restart之后继续单调递增。
    sequence: int
    # 稳定事件类型供声音和展示消费。
    kind: str
    # 可选详情为稳定ID或玩家反馈。
    detail: str = ""
