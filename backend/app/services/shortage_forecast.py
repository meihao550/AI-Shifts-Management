"""人手不足の予測（将来の各スロットで規定人数に届かなくなる度合いを予測する）。

need(必要人数)は固定ルールなので「需要そのもの」は学習しない。ここでは履歴(CoverageOutcome)から
「どのスロットで不足(shortage)が起きやすいか」をカレンダー特徴＋必要人数＋容量(その時間に入れる
従業員数)から予測する。容量が need に足りないほど不足が起きやすい、という関係を学習する。

Strategy で予測器を差し替え可能にする（LLM provider と同方針）:
  - 履歴が十分: numpy の Ridge 回帰（SeasonalBaseline では表せない必要人数/容量/祝日の効果も学習）
  - 履歴が少ない/学習失敗: 季節平均ベースライン（(weekday, hour) ごとの平均不足）に自動フォールバック
学習はリクエスト時にオンデマンド（小データなので安価・モデル永続化不要）。sklearn は使わない
（Cloud Run のイメージ肥大・コールドスタート悪化を避ける＝軽量運用方針。ADR-0013）。
"""

from __future__ import annotations

import calendar
from datetime import date
from typing import NamedTuple, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.coverage_outcome import CoverageOutcome
from app.models.employee import Employee
from app.schemas.analytics import ForecastSlot, ShortageForecast
from app.services.holidays import category_for, is_holiday
from app.services.scheduler import window_hours_for
from app.services.staffing import load_staffing_map

# Ridge(numpy) を使う最小の月数・行数。これ未満は季節平均ベースラインにフォールバックする。
MIN_MONTHS_FOR_MODEL = 3
MIN_ROWS_FOR_MODEL = 200
# Ridge 回帰の正則化係数（小データで過学習しないよう少し強めに効かせる）。
RIDGE_LAMBDA = 1.0


class SlotFeatures(NamedTuple):
    """予測の1スロットを表す特徴の素。学習(fit)と予測(predict)で同じものを使う。"""

    weekday: int  # 0=月 … 6=日
    hour: int  # 拡張時軸 0〜24+
    is_hol: bool  # 祝日か
    day_category: str  # "weekday" | "weekend_or_holiday"
    required: int  # 必要人数（固定ルール由来）
    available: int  # その時間に入れる従業員数（容量）
    active: int  # 有効従業員数（ロスター規模）


def _busy(day_category: str) -> float:
    """繁忙区分(金土日祝)なら 1.0。特徴量に使う。"""
    return 1.0 if day_category == "weekend_or_holiday" else 0.0


def _vector(f: SlotFeatures) -> list[float]:
    """特徴ベクトル（bias + 曜日one-hot + 時/祝日/繁忙/必要人数/容量/ロスター規模）。"""
    wd = [0.0] * 7
    if 0 <= f.weekday <= 6:
        wd[f.weekday] = 1.0
    return [
        1.0,
        *wd,
        f.hour / 24.0,
        1.0 if f.is_hol else 0.0,
        _busy(f.day_category),
        float(f.required),
        float(f.available),
        float(f.active),
    ]


def _row_features(r: CoverageOutcome) -> SlotFeatures:
    """CoverageOutcome 1行を SlotFeatures にする（学習データ化）。"""
    return SlotFeatures(
        weekday=r.weekday,
        hour=r.hour,
        is_hol=r.is_holiday,
        day_category=r.day_category,
        required=r.required,
        available=r.available_employees,
        active=r.active_employees,
    )


class ShortageForecaster(Protocol):
    """スロットの不足人数を予測する戦略。method はどう算出したか(model/baseline)を表す。"""

    method: str

    def predict(self, f: SlotFeatures) -> float:
        """1スロットの予測不足人数（0 以上）を返す。"""
        ...


class SeasonalBaseline:
    """(weekday, hour) ごとの平均不足を返す素朴なベースライン。履歴が少なくても安定。"""

    method = "baseline"

    def __init__(self, rows: list[CoverageOutcome]) -> None:
        """履歴から (weekday, hour) ごとの平均不足と全体平均を事前計算する。"""
        sums: dict[tuple[int, int], float] = {}
        counts: dict[tuple[int, int], int] = {}
        total = 0.0
        for r in rows:
            key = (r.weekday, r.hour)
            sums[key] = sums.get(key, 0.0) + r.shortage
            counts[key] = counts.get(key, 0) + 1
            total += r.shortage
        self._mean = {k: sums[k] / counts[k] for k in sums}
        self._global = total / len(rows) if rows else 0.0

    def predict(self, f: SlotFeatures) -> float:
        """該当 (weekday, hour) の平均不足。未知のスロットは全体平均で埋める。"""
        return self._mean.get((f.weekday, f.hour), self._global)


class RidgeModel:
    """numpy の Ridge 回帰。カレンダー特徴＋必要人数＋容量から不足人数を予測する。"""

    method = "model"

    def __init__(self, rows: list[CoverageOutcome]) -> None:
        """履歴から設計行列を組み、閉形式の Ridge 回帰で重みを解く。"""
        import numpy as np

        x = np.array([_vector(_row_features(r)) for r in rows])
        y = np.array([float(r.shortage) for r in rows])
        d = x.shape[1]
        # w = (XᵀX + λI)⁻¹ Xᵀy。bias 項(列0)は正則化しない。
        reg = RIDGE_LAMBDA * np.eye(d)
        reg[0, 0] = 0.0
        self._w = np.linalg.solve(x.T @ x + reg, x.T @ y)

    def predict(self, f: SlotFeatures) -> float:
        """特徴ベクトルと重みの内積。不足は非負なので 0 で下限クリップする。"""
        import numpy as np

        return max(0.0, float(np.array(_vector(f)) @ self._w))


def _distinct_months(rows: list[CoverageOutcome]) -> int:
    """履歴に含まれる (年, 月) の種類数。学習データ量の目安。"""
    return len({(r.target_date.year, r.target_date.month) for r in rows})


def resolve_forecaster(rows: list[CoverageOutcome]) -> ShortageForecaster:
    """履歴量に応じて予測器を選ぶ。十分なら Ridge、少ない/失敗ならベースライン。"""
    if _distinct_months(rows) >= MIN_MONTHS_FOR_MODEL and len(rows) >= MIN_ROWS_FOR_MODEL:
        try:
            return RidgeModel(rows)
        except Exception:
            # 学習に失敗しても予測は止めない（安全側＝ベースライン）。
            return SeasonalBaseline(rows)
    return SeasonalBaseline(rows)


def _caveat(method: str, months: int) -> str | None:
    """データ量に応じた注意書き（UI でバッジ表示。先方を誤認させないため）。"""
    if method == "none":
        return "まだシフト生成の履歴がありません。シフトを生成すると予測できるようになります。"
    if method == "baseline":
        return (
            f"履歴が少ない（{months}ヶ月分）ため参考値です（季節平均ベースライン）。"
            "数ヶ月分が貯まると予測精度が上がります。"
        )
    return f"過去{months}ヶ月分の実績から予測しています。"


def forecast_month(db: Session, year: int, month: int) -> ShortageForecast:
    """対象月の各 (日・拡張時) について人手不足の予測を返す。

    必要人数は固定ルール(load_staffing_map)、容量は現在の有効従業員の勤務可能時間帯から算出し、
    曜日/祝日/繁忙区分と合わせて予測器に渡す。あくまで「規定に対する不足の起きやすさ」の目安。
    """
    rows = list(db.execute(select(CoverageOutcome)).scalars())
    months = _distinct_months(rows)
    forecaster = resolve_forecaster(rows)
    method = forecaster.method if rows else "none"

    staffing_map = load_staffing_map(db)
    by_cat: dict[str, list[tuple[int, int]]] = {}
    for (dc, hour), req in staffing_map.items():
        by_cat.setdefault(dc, []).append((hour, req))

    # 現在の有効従業員から容量（その時間に入れる人数）を算出する。
    emps = list(db.execute(select(Employee).where(Employee.active.is_(True))).scalars())
    active = len(emps)
    win_by_emp = {
        e.id: window_hours_for(e.available_start_hour, e.available_end_hour) for e in emps
    }

    def available_at(hour: int) -> int:
        """その拡張時に入れる（窓内 or 窓未設定の）従業員数。"""
        return sum(1 for e in emps if win_by_emp[e.id] is None or hour in win_by_emp[e.id])

    _, last_day = calendar.monthrange(year, month)
    slots: list[ForecastSlot] = []
    for day in range(1, last_day + 1):
        d = date(year, month, day)
        cat = category_for(d)
        hol = is_holiday(d)
        for hour, required in sorted(by_cat.get(cat, [])):
            if method == "none":
                pred = 0.0
            else:
                feat = SlotFeatures(
                    weekday=d.weekday(),
                    hour=hour,
                    is_hol=hol,
                    day_category=cat,
                    required=required,
                    available=available_at(hour),
                    active=active,
                )
                pred = forecaster.predict(feat)
            slots.append(
                ForecastSlot(
                    target_date=d.isoformat(),
                    weekday=d.weekday(),
                    hour=hour,
                    predicted_shortage=round(pred, 2),
                    required=required,
                )
            )

    return ShortageForecast(
        year=year,
        month=month,
        method=method,
        data_months=months,
        caveat=_caveat(method, months),
        slots=slots,
    )
