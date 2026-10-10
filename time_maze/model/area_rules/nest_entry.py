# 巢后通道只在孩童夜间安全入场时刷新完整检查点。
def is_safe_nest_entry(region: str, age: str, is_day: bool) -> bool:
    # 区域规则只查询传入值，状态恢复仍由会话协调。
    return region == "F" and age == "child" and not is_day
