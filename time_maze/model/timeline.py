# 时代与昼夜只保存业务值，不读取电脑时钟。
class Timeline:
    # 游戏从孩童白天开始，两种状态互相独立。
    def __init__(self, age: str = "child", is_day: bool = True):
        # 构造与完整恢复共用实际输入校验。
        self.restore(age, is_day)

    # 查询当前年龄能力。
    @property
    def age(self) -> str:
        # 返回child或adult。
        return self._age

    # 年份与年龄一一对应，无真实日期依赖。
    @property
    def year(self) -> int:
        # 两时代固定相隔七年。
        return 2026 if self._age == "child" else 2033

    # 所有门与鸡共享同一昼夜。
    @property
    def is_day(self) -> bool:
        # 返回真正已提交的状态。
        return self._is_day

    # 已通过剑台验证后才提交年龄切换。
    def toggle_age(self) -> None:
        # 切龄保留当前昼夜。
        self._age = "adult" if self._age == "child" else "child"

    # 已匹配原创时间曲后切換昼夜。
    def toggle_day(self) -> None:
        # 同一首曲的作用取决于当前昼夜。
        self._is_day = not self._is_day

    # 恢复完整业务快照，参数来自本局不可变检查点。
    def restore(self, age: str, is_day: bool) -> None:
        # 年龄和昼夜必须各自为合法明确状态。
        if type(age) is not str or age not in ("child", "adult") or type(is_day) is not bool:
            # 不以默认年龄或bool转换掩盖错误。
            raise ValueError("时代恢复需要child/adult和真实bool")
        # 年龄和相位一起还原，不留下半恢复状态。
        self._age = age
        # 相位不从年份或电脑日期反推。
        self._is_day = is_day
