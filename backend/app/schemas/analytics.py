"""人手不足の集計・予測 API のスキーマ。"""

from pydantic import BaseModel


class ShortageSlotStat(BaseModel):
    """曜日×拡張時の1スロットについての人手不足の実績統計。"""

    weekday: int  # 0=月 … 6=日
    hour: int  # 拡張時軸 0〜24+（24=翌0:00）
    samples: int  # 集計対象の日数（= 該当する CoverageOutcome 行数）
    shortage_rate: float  # 不足が出た割合（0.0〜1.0）
    avg_shortage: float  # 平均不足人数
    avg_required: float  # 平均必要人数
    avg_filled: float  # 平均実配置人数


class ShortageAnalytics(BaseModel):
    """曜日×時間帯の慢性的な人手不足の集計結果。"""

    months: int  # 蓄積された月数（データ量の目安）
    total_slots: int  # 集計に使った CoverageOutcome 行数
    slots: list[ShortageSlotStat]  # weekday×hour グリッド（実績のある全スロット）
    ranking: list[ShortageSlotStat]  # 不足しやすい順の上位スロット


class ForecastSlot(BaseModel):
    """ある日・拡張時についての人手不足の予測。"""

    target_date: str  # ISO 日付（YYYY-MM-DD）
    weekday: int
    hour: int
    predicted_shortage: float  # 予測される不足人数（期待値）
    required: int  # その日時の必要人数（固定ルール由来）


class ShortageForecast(BaseModel):
    """対象月の人手不足予測（スロット別）＋どう算出したかのメタ情報。"""

    year: int
    month: int
    method: str  # "model"（学習モデル） | "baseline"（季節平均） | "none"（データ無し）
    data_months: int  # 学習に使えた月数
    # データが少ない間は参考値である旨の注意書き（UI でバッジ表示）。
    caveat: str | None = None
    slots: list[ForecastSlot]
