# 用冻结数据类保存独立于底图的交互物定义。
from dataclasses import dataclass

# 运行时开合状态不写回该静态对象。
# 冻结数据类禁止字段重赋值，嵌套容器另按模型边界核验。
@dataclass(frozen=True)
class InteractiveObject:
    # ID用于保存领取状态，不通过名称识别对象。
    id: str
    # kind区分剑、货箱、谱箱、奖励箱和鸡巢。
    kind: str
    # 动态素材占位由格坐标给出。
    position: tuple[int, int]
    # 谱箱等对象引用稳定内容ID。
    payload: str = ""
    # 推物的唯一停放格独立于美术，其他物件没有推物目标。
    target_position: tuple[int, int] | None = None
