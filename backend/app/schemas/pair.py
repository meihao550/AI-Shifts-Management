"""
PydanticのBaseModelを継承したクラス群
フロントからきたJsonが正しい型・範囲かを検査する。おかしければFastAPIが自動で422を返す。
ドキュメント生成をしてくれる（自動で）
"""

from pydantic import BaseModel, ConfigDict, model_validator

"""ReadとCreateでidがあったりなかったりする理由：
Create時にはidはDBが番号を割り当てるのでこちらで定義する必要がない。
"""


class PairConstraintCreate(BaseModel):
    employee_a_id: int
    employee_b_id: int

    @model_validator(mode="after")
    def _reject_self_pair(self) -> "PairConstraintCreate":
        # 同一人物同士のペアは意味がないので弾く（422 になる）
        if self.employee_a_id == self.employee_b_id:
            raise ValueError("employee_a_id と employee_b_id は別の従業員である必要があります")
        return self


class PairConstraintRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_a_id: int
    employee_b_id: int
