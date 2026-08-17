from pydantic import BaseModel


# Notificationは、通知を送る際の型を指定している。
# levelは、warning info error success というNaive UI(frontend ライブラリ)のtypeに対応
# pydantic のBaseModelの解説【https://qiita.com/ReSpade/items/5f9d6e06de3591f4bda7】
class Notification(BaseModel):
    kind: str
    level: str
    message: str
    target_year: int | None = None
    target_month: int | None = None
