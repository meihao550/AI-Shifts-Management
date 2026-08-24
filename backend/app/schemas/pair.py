"""
PydanticのBaseModelを継承したクラス群
フロントからきたJsonが正しい型・範囲かを検査する。おかしければFastAPIが自動で422を返す。
ドキュメント生成をしてくれる（自動で）
"""

from pydantic import BaseModel, ConfigDict

"""ReadとCreateでidがあったりなかったりする理由：
Create時にはidはDBが番号を割り当てるのでこちらで定義する必要がない。
"""


class PairConstraintCreate(BaseModel):
    employee_a_id: int
    employee_b_id: int


class PairConstraintRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_a_id: int
    employee_b_id: int
