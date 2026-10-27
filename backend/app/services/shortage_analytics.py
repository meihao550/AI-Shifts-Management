"""人手不足の集計（曜日×時間帯の慢性的な不足を CoverageOutcome から集計する）。

need(必要人数)は固定ルールなので学習/集計対象ではなく、ここでは「どのスロットで配置が
届かなかったか（shortage）」を曜日×時間帯で集計して、慢性的な人手不足を可視化する。
ML を使わない素朴な集計で、履歴が少なくても実装直後から有用。
"""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.coverage_outcome import CoverageOutcome
from app.schemas.analytics import ShortageAnalytics, ShortageSlotStat


def aggregate_shortage(db: Session, ranking_limit: int = 12) -> ShortageAnalytics:
    """CoverageOutcome を曜日×拡張時でまとめ、スロット別の不足統計とランキングを返す。

    各スロットについて 平均不足 / 不足発生率(不足した日の割合) / 平均必要人数 / 平均実配置 を出す。
    ランキングは「不足発生率 → 平均不足」の降順で、不足が出たことのあるスロットのみ上位を返す。
    """
    rows = list(db.execute(select(CoverageOutcome)).scalars())

    # (weekday, hour) ごとに行をまとめる
    groups: dict[tuple[int, int], list[CoverageOutcome]] = defaultdict(list)
    months: set[tuple[int, int]] = set()
    for r in rows:
        groups[(r.weekday, r.hour)].append(r)
        months.add((r.target_date.year, r.target_date.month))

    slots: list[ShortageSlotStat] = []
    for (weekday, hour), items in groups.items():
        n = len(items)
        short_count = sum(1 for it in items if it.shortage > 0)
        slots.append(
            ShortageSlotStat(
                weekday=weekday,
                hour=hour,
                samples=n,
                shortage_rate=short_count / n,
                avg_shortage=sum(it.shortage for it in items) / n,
                avg_required=sum(it.required for it in items) / n,
                avg_filled=sum(it.filled for it in items) / n,
            )
        )
    slots.sort(key=lambda s: (s.weekday, s.hour))

    ranking = sorted(
        (s for s in slots if s.avg_shortage > 0),
        key=lambda s: (s.shortage_rate, s.avg_shortage),
        reverse=True,
    )[:ranking_limit]

    return ShortageAnalytics(
        months=len(months),
        total_slots=len(rows),
        slots=slots,
        ranking=ranking,
    )
