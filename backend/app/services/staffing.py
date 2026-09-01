"""シフトパターン・時間別必要人数のデフォルト定義（seed / 初回自動投入で共有）。

時間カバレッジ方式（要件書§13）では、営業日を 1:00 起点で扱い、
必要人数を「拡張時(hour)」ごとに持つ。24=翌0:00, 25=翌1:00。
"""

from __future__ import annotations

from datetime import time

from app.models.rule import DayCategory


def default_patterns() -> list[dict]:
    """基本パターン(朝/夜/深夜) + Wワーク向けの不定時刻パターン。"""
    return [
        # --- 基本パターン ---
        {
            "code": "morning",
            "label": "朝 09:00-17:00",
            "start_time": time(9, 0),
            "end_time": time(17, 0),
            "is_basic": True,
            "category": "morning",
        },
        {
            "code": "evening",
            "label": "夜 17:00-01:00",
            "start_time": time(17, 0),
            "end_time": time(1, 0),
            "is_basic": True,
            "category": "evening",
        },
        {
            "code": "night",
            "label": "深夜 01:00-09:00",
            "start_time": time(1, 0),
            "end_time": time(9, 0),
            "is_basic": True,
            "category": "night",
        },
        # --- Wワーク向け（不定時刻） ---
        {
            "code": "w_09_15",
            "label": "Wワーク 09:00-15:00",
            "start_time": time(9, 0),
            "end_time": time(15, 0),
            "is_basic": False,
            "category": "morning",
        },
        {
            "code": "w_12_20",
            "label": "Wワーク 12:00-20:00",
            "start_time": time(12, 0),
            "end_time": time(20, 0),
            "is_basic": False,
            "category": "evening",
        },
        {
            "code": "w_20_01",
            "label": "Wワーク 20:00-01:00",
            "start_time": time(20, 0),
            "end_time": time(1, 0),
            "is_basic": False,
            "category": "evening",
        },
    ]


# 1時間ごとの必要人数のデフォルト（拡張時 1..24）。
# 深夜(1-8) は 1 人、営業ピークの朝(9-16)・夜(17-24) は平日2/土日祝3 人。
def default_hourly_rules() -> list[dict]:
    rules: list[dict] = []

    def add(day_category: DayCategory, hours: range, required: int) -> None:
        for h in hours:
            rules.append(
                {"day_category": day_category, "hour": h, "required": required}
            )

    # 平日
    add(DayCategory.weekday, range(1, 9), 1)  # 深夜 1:00-9:00
    add(DayCategory.weekday, range(9, 17), 2)  # 朝 9:00-17:00
    add(DayCategory.weekday, range(17, 25), 2)  # 夜 17:00-翌1:00
    # 土日祝
    add(DayCategory.weekend_or_holiday, range(1, 9), 1)
    add(DayCategory.weekend_or_holiday, range(9, 17), 3)
    add(DayCategory.weekend_or_holiday, range(17, 25), 3)

    return rules
