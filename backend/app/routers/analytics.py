"""人手不足の集計・予測 API（管理者のみ）。"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import AdminUser
from app.core.database import get_db
from app.schemas.analytics import ShortageAnalytics
from app.services import shortage_analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/shortage", response_model=ShortageAnalytics)
def get_shortage_analytics(
    _admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    """曜日×時間帯の慢性的な人手不足の集計を返す（管理者のみ）。

    シフト生成のたびに貯まる CoverageOutcome を集計し、どの曜日・時間帯で規定人数に
    届きにくいかを可視化する。need(必要人数)は固定ルールのため、ここでは不足の実績を集計する。
    """
    return shortage_analytics.aggregate_shortage(db)
