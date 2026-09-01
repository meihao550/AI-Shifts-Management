"""シフトパターン・時間別必要人数のデフォルト定義（seed / 初回自動投入で共有）。

時間カバレッジ方式（要件書§13）では、営業日を 1:00 起点で扱い、
必要人数を「拡張時(hour)」ごとに持つ。24=翌0:00, 25=翌1:00。

シフトパターンは要件6.1/6.2の標準セットをシステム側で用意する。ユーザーは
コードや区分を手入力せず、時刻(開始-終了)だけで追加できる（コード/区分は自動生成）。
"""

from __future__ import annotations

from datetime import time

from app.models.rule import DayCategory


def make_pattern_code(start: time, end: time) -> str:
    """時刻からパターンコードを自動生成する（例 09:00-17:00 -> p_0900_1700）。"""
    return f"p_{start.strftime('%H%M')}_{end.strftime('%H%M')}"


def make_pattern_label(start: time, end: time) -> str:
    """時刻から表示名を自動生成する（例 09:00-17:00）。"""
    return f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"


def infer_category(start: time, end: time) -> str:
    """時刻から区分(morning/evening/night)を自動判定する。

    区分は必要人数の判定には使わない（時間カバレッジで判定）。
    メインシフトの寄せ（ボーナス）でのみ参照するため、大まかで良い。
    """
    s = start.hour
    e = end.hour
    if 1 <= s < 9 and (s < e <= 9):  # 1:00-9:00 のような深夜帯
        return "night"
    if s < 12:  # 昼までに始まる → 朝
        return "morning"
    return "evening"  # それ以降 → 夜


# 要件6.2 のWワーク（不定時刻）パターン。＋金土祝の追加要員 22-1（要確認）も含める。
_WWORK_HOURS: list[tuple[int, int]] = [
    (9, 15),
    (9, 16),
    (10, 17),
    (10, 18),
    (12, 20),
    (15, 23),
    (18, 20),
    (18, 1),
    (20, 1),
    (22, 1),
]


def default_patterns() -> list[dict]:
    """基本パターン(要件6.1) + Wワーク向けの不定時刻パターン(要件6.2)。"""
    patterns: list[dict] = [
        # --- 基本パターン（コードは意味のある名前を維持） ---
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
    ]
    # --- Wワーク向け（不定時刻）。コード/区分は自動生成 ---
    for sh, eh in _WWORK_HOURS:
        st, et = time(sh, 0), time(eh, 0)
        patterns.append(
            {
                "code": make_pattern_code(st, et),
                "label": make_pattern_label(st, et),
                "start_time": st,
                "end_time": et,
                "is_basic": False,
                "category": infer_category(st, et),
            }
        )
    return patterns


# 1時間ごとの必要人数のデフォルト（拡張時 1..24）。要件6.3/6.4。
#
# 平日は基本パターン(9-17/17-1/1-9)だけで一律に充足する。
# 金・土・日・祝の「+1名」は繁忙ピーク帯だけに置き、そのピークは基本パターンでは
# 過剰(==違反)になって埋められない形にする。すると solver は Wワーク専用パターン
# （10-17 や 18-1 など。掛け持ち従業員のみ配置可）を使わざるを得なくなり、
# 過剰配置なし(==維持)のまま Wワークの人が繁忙帯に入る（方針B: ピーク運用）。
def default_hourly_rules() -> list[dict]:
    rules: list[dict] = []

    def add(day_category: DayCategory, hours: range, required: int) -> None:
        for h in hours:
            rules.append(
                {"day_category": day_category, "hour": h, "required": required}
            )

    # 平日（月〜木）: 深夜1 / 朝2 / 夜2（すべて基本パターンで充足）
    add(DayCategory.weekday, range(1, 9), 1)  # 深夜 1:00-9:00
    add(DayCategory.weekday, range(9, 17), 2)  # 朝 9:00-17:00
    add(DayCategory.weekday, range(17, 25), 2)  # 夜 17:00-翌1:00

    # 金・土・日・祝（繁忙区分）: 深夜1 / 朝は10-16がピークで+1 / 夜は18-24がピークで+1
    add(DayCategory.weekend_or_holiday, range(1, 9), 1)  # 深夜 1:00-9:00
    add(DayCategory.weekend_or_holiday, range(9, 10), 2)  # 9時台は2（基本2枚）
    add(DayCategory.weekend_or_holiday, range(10, 17), 3)  # 10-16時が朝ピーク +1 → 10-17(W)
    add(DayCategory.weekend_or_holiday, range(17, 18), 2)  # 17時台は2（基本2枚）
    add(DayCategory.weekend_or_holiday, range(18, 25), 3)  # 18-24時が夜ピーク +1 → 18-1(W)

    return rules
