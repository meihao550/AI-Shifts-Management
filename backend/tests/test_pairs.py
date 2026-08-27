"""禁止ペア スキーマ（PairConstraintCreate）のバリデーションテスト。"""

import pytest
from pydantic import ValidationError

from app.schemas.pair import PairConstraintCreate


def test_valid_pair_is_accepted():
    obj = PairConstraintCreate(employee_a_id=1, employee_b_id=2)
    assert obj.employee_a_id == 1
    assert obj.employee_b_id == 2


def test_self_pair_is_rejected():
    # 同一人物同士のペアは弾かれる（API では 422 になる）
    with pytest.raises(ValidationError):
        PairConstraintCreate(employee_a_id=1, employee_b_id=1)
