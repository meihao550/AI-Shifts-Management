# 必要ライブラリの呼び出し
from datetime import date

from sqlalchemy.orm import Session

from app.schemas.notification import Notification

# 通知する日をここで指定
REMIND_DAY = 26


# 次の月を取得する。12月なら1月のロジックを取らないといけない。
# returnには２つのタプルの戻り値が返る。
def _next_month(d: date) -> tuple[int, int]:
    if d.month == 12:
        return (d.year + 1, 1)
    else:
        return (d.year, d.month + 1)


# 26日に近くなったら来月のシフトができているかDBに問い合わせる。
# まだなら通知を出す。
def build_notifications(db: Session, today: date) -> list[Notification]:
    result: list[Notification] = []
