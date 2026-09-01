"""Japanese holiday helpers."""

from datetime import date

import jpholiday


def is_holiday(d: date) -> bool:
    return jpholiday.is_holiday(d)


def is_weekend_or_holiday(d: date) -> bool:
    return d.weekday() >= 5 or is_holiday(d)


def is_busy_day(d: date) -> bool:
    """繁忙区分（必要人数が多い日）。要件6.3: 金・土・日・祝が対象。

    Python の weekday() は 月=0 … 金=4, 土=5, 日=6。金曜(4)以降＋祝日を繁忙とする。
    """
    return d.weekday() >= 4 or is_holiday(d)


def category_for(d: date) -> str:
    # 必要人数の区分。金・土・日・祝は繁忙区分（要件6.3）。
    return "weekend_or_holiday" if is_busy_day(d) else "weekday"
