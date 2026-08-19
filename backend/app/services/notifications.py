# 必要ライブラリの呼び出し
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.shift import Shift, ShiftStatus
from app.schemas.notification import Notification

# 通知する日をここで指定 定数。
REMIND_DAY = 26


# 次の月を取得する。12月なら1月のロジックを取らないといけない。
# returnには２つのタプルの戻り値が返る。
def _next_month(d: date) -> tuple[int, int]:
    if d.month == 12:
        return (d.year + 1, 1)  # 2026年の12月なら、2027年の1月が出力される。
    else:
        return (d.year, d.month + 1)


# 26日に近くなったら来月のシフトができているかDBに問い合わせる。
# まだなら通知を出す。
def build_notifications(db: Session, today: date) -> list[Notification]:
    result: list[Notification] = []

    if today.day >= REMIND_DAY:
        y, m = _next_month(today)  # 上の_next_month関数をy, mという変数に入れる。
        # シフトのDBを問い合わせて件数があるかどうか確認
        shift = db.execute(
            select(Shift).where(Shift.year == y, Shift.month == m)
        ).scalar_one_or_none()

        # draftは、シフトがまだ決まってないステータスを意味する。
        # そのためこのif文は翌日シフトがないか、下書きなら最速の通知を出すよーっていう通知ロジック
        if shift is None or shift.status == ShiftStatus.draft:
            result.append(
                Notification(
                    kind="shift_reminder",
                    level="warning",
                    message=f"{y}年{m}月のシフトがまだ確定していません。作成してください。",
                    target_year=y,
                    target_month=m,
                )
            )
    return result
