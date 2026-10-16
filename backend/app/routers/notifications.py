from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.core.database import get_db

# Notificationsのリストをもってくる
from app.schemas.notification import Notification
from app.services.notifications import build_notifications

router = APIRouter(prefix="/notifications", tags=["notifications"])

# 引数をみやすくするために分けました
# ここでAnnotatedを使う理由(https://fastapi.tiangolo.com/tutorial/query-params-str-validations/#advantages-of-annotated)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[Notification])
def list_notifications(_user: CurrentUser, db: DatabaseSession):
    """ダッシュボード用の通知一覧を返す（日本時間の今日を基準に組み立て）。"""
    today = datetime.now(ZoneInfo("Asia/Tokyo")).date()
    return build_notifications(db, today)
