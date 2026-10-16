"""初期マスタ（シフトパターン・時間別必要人数）の投入ヘルパー。

開発用 /dev/seed と本番 seed スクリプトで共有する。冪等（未登録のときだけ投入）。
注意: シフト生成(shifts.py)の自動投入はパターンのみ永続化し必要人数は永続化しない
別挙動のため、ここは共有していない。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rule import HourlyStaffingRule, ShiftPattern
from app.services.staffing import default_hourly_rules, default_patterns


def seed_defaults_if_missing(db: Session) -> None:
    """シフトパターン・時間別必要人数が未登録なら既定値を投入する（commit は呼び出し側）。"""
    if not db.execute(select(ShiftPattern)).first():
        db.add_all([ShiftPattern(**p) for p in default_patterns()])
    if not db.execute(select(HourlyStaffingRule)).first():
        db.add_all([HourlyStaffingRule(**r) for r in default_hourly_rules()])
