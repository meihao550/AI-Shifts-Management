"""Japanese holiday helpers."""

from datetime import date

import jpholiday


def is_holiday(d: date) -> bool:
    return jpholiday.is_holiday(d)


def is_weekend_or_holiday(d: date) -> bool:
    return d.weekday() >= 5 or is_holiday(d)


def category_for(d: date) -> str:
    return "weekend_or_holiday" if is_weekend_or_holiday(d) else "weekday"
