"""日付まわりの共通ヘルパー。"""

from datetime import date


def month_range(year: int, month: int) -> tuple[date, date]:
    """対象月の半開区間 [月初, 翌月初) を返す。

    `target_date >= start AND target_date < end` で当月レコードを絞り込むのに使う。
    12 月は翌年 1/1 を終端にする。
    """
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end
