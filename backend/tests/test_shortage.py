"""人手不足の集計(shortage_analytics)と予測(shortage_forecast)のテスト。

CoverageOutcome を sqlite に積んで、曜日×時間の集計・ランキング・予測器の
フォールバック（データ量に応じた baseline / model 切替）を検証する。
"""

import calendar
from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401  全モデルを metadata に登録する
from app.core.database import Base
from app.models.coverage_outcome import CoverageOutcome
from app.models.shift import Shift, ShiftStatus
from app.services.shortage_analytics import aggregate_shortage
from app.services.shortage_forecast import (
    SeasonalBaseline,
    forecast_month,
    resolve_forecaster,
)


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _shift(db: Session, year: int, month: int) -> Shift:
    sh = Shift(year=year, month=month, status=ShiftStatus.draft)
    db.add(sh)
    db.commit()
    return sh


def _add(db: Session, shift_id: int, d: date, hour: int, required: int, filled: int) -> None:
    db.add(
        CoverageOutcome(
            shift_id=shift_id,
            target_date=d,
            hour=hour,
            day_category="weekend_or_holiday" if d.weekday() >= 4 else "weekday",
            weekday=d.weekday(),
            is_holiday=False,
            required=required,
            filled=filled,
            shortage=max(required - filled, 0),
        )
    )


# ---- 集計 ----------------------------------------------------------------------


def test_aggregate_groups_by_weekday_hour():
    db = _db()
    sh = _shift(db, 2026, 10)
    # 金曜18時(req3): filled 1 と 3 → shortage 2 と 0
    _add(db, sh.id, date(2026, 10, 2), 18, 3, 1)
    _add(db, sh.id, date(2026, 10, 9), 18, 3, 3)
    db.commit()

    a = aggregate_shortage(db)
    assert a.months == 1
    assert a.total_slots == 2
    slot = next(s for s in a.slots if s.weekday == 4 and s.hour == 18)
    assert slot.samples == 2
    assert slot.shortage_rate == 0.5
    assert slot.avg_shortage == 1.0
    assert slot.avg_required == 3.0
    assert slot.avg_filled == 2.0


def test_ranking_orders_by_rate_then_shortage():
    db = _db()
    sh = _shift(db, 2026, 10)
    # 金18時: 毎回大きく不足
    _add(db, sh.id, date(2026, 10, 2), 18, 3, 0)
    _add(db, sh.id, date(2026, 10, 9), 18, 3, 0)
    # 土10時: たまに小さく不足
    _add(db, sh.id, date(2026, 10, 3), 10, 2, 2)
    _add(db, sh.id, date(2026, 10, 10), 10, 2, 1)
    db.commit()

    a = aggregate_shortage(db)
    assert len(a.ranking) == 2
    # 不足率・平均不足とも大きい金18時が先頭
    assert a.ranking[0].weekday == 4 and a.ranking[0].hour == 18


# ---- 予測 ----------------------------------------------------------------------


def test_forecaster_empty_is_none():
    db = _db()
    f = forecast_month(db, 2026, 11)
    assert f.method == "none"
    assert f.caveat
    assert f.slots  # ルールのデフォルトでスロットは生成される
    assert all(s.predicted_shortage == 0.0 for s in f.slots)


def test_forecaster_few_data_uses_baseline():
    db = _db()
    sh = _shift(db, 2026, 10)
    for day, filled in [(2, 1), (9, 1), (16, 2)]:
        _add(db, sh.id, date(2026, 10, day), 18, 3, filled)
    db.commit()

    rows = list(db.execute(select(CoverageOutcome)).scalars())
    assert isinstance(resolve_forecaster(rows), SeasonalBaseline)

    f = forecast_month(db, 2026, 11)
    assert f.method == "baseline"
    # 金曜18時 → shortage (2,2,1) の平均 ≒ 1.67
    fri = [s for s in f.slots if s.weekday == 4 and s.hour == 18]
    assert fri and abs(fri[0].predicted_shortage - 1.67) < 0.01


def test_forecaster_model_predictions_non_negative():
    db = _db()
    for ym in [(2026, 7), (2026, 8), (2026, 9)]:
        sh = _shift(db, *ym)
        _, last = calendar.monthrange(*ym)
        for day in range(1, last + 1):
            d = date(ym[0], ym[1], day)
            busy = d.weekday() >= 4
            for hour in range(9, 25):
                req = 3 if busy and 10 <= hour < 17 else 2
                short = 2 if (d.weekday() == 4 and hour >= 18) else 0
                _add(db, sh.id, d, hour, req, max(0, req - short))
        db.commit()

    rows = list(db.execute(select(CoverageOutcome)).scalars())
    assert resolve_forecaster(rows).method == "model"

    f = forecast_month(db, 2026, 10)
    assert f.method == "model"
    assert f.data_months == 3
    assert all(s.predicted_shortage >= 0 for s in f.slots)
