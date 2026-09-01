from datetime import time

from pydantic import BaseModel, ConfigDict

from app.models.rule import DayCategory


class ShiftPatternBase(BaseModel):
    code: str
    label: str
    start_time: time
    end_time: time
    is_basic: bool = True
    category: str  # morning | evening | night


# 追加は「時刻(開始-終了)」だけ。コード/表示名/区分/is_basic はサーバ側で自動生成する
# （ユーザーにコードや区分を入力させない。要件10.5）。
class ShiftPatternCreate(BaseModel):
    start_time: time
    end_time: time
    label: str | None = None  # 未指定なら時刻から自動生成


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
