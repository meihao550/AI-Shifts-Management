from datetime import time

from pydantic import BaseModel, ConfigDict, Field

from app.models.rule import DayCategory


class ShiftPatternBase(BaseModel):
    code: str
    label: str
    start_time: time
    end_time: time
    category: str  # morning | evening | night
    rest_minutes: int = 0  # 休憩時間（分）


# 追加は「時刻(開始-終了)+休憩」だけ。コード/表示名/区分はサーバ側で自動生成する
# （ユーザーにコードや区分を入力させない。要件10.5）。
class ShiftPatternCreate(BaseModel):
    start_time: time
    end_time: time
    label: str | None = None  # 未指定なら時刻から自動生成
    rest_minutes: int = Field(default=0, ge=0)


# 編集は表示中の項目（表示名・開始・終了・休憩）を対象にする。未指定の項目は変更しない。
class ShiftPatternUpdate(BaseModel):
    label: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    rest_minutes: int | None = Field(default=None, ge=0)


class ShiftPatternRead(ShiftPatternBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class HourlyStaffingRuleBase(BaseModel):
    day_category: DayCategory
    hour: int  # 拡張時軸（0〜25）。24=翌0:00, 25=翌1:00
    required: int


class HourlyStaffingRuleCreate(HourlyStaffingRuleBase):
    pass


class HourlyStaffingRuleRead(HourlyStaffingRuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
