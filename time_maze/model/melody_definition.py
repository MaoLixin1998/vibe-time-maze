# 曲谱定义只保存音符与稳定效果，不包含音频资源。
from dataclasses import dataclass

# 冻结后的曲谱同时供匹配和玩家谱册展示。
# 冻结数据类禁止字段重赋值，嵌套容器另按模型边界核验。
@dataclass(frozen=True)
class MelodyDefinition:
    # 谱ID与宝箱payload引用一致。
    id: str
    # 玩家可读的曲目名称。
    name: str
    # 每音由数字1至7及八度0或1组成。
    notes: tuple[tuple[int, int], ...]
    # 业务效果ID与音色、显示文字分离。
    effect: str
    # main、optional和hidden区分展示用途。
    category: str
