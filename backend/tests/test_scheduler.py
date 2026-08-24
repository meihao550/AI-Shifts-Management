"""制約問題のテストコード"""
# 制約問題はテストを先に作らないとコーディングがあってるかどうかわからないのでつくります

from app.services.scheduler import EmployeeSpec  # この三つは型定義してるだけ


def test_forbidden_pair_makes_infeasible():
    employee_a = EmployeeSpec(
        id=1, name="A", weekly_target=7, main_shift_type="morning", hourly_wage=1000
    )
    employee_b = EmployeeSpec(
        id=2, name="B", weekly_target=7, main_shift_type="morning", hourly_wage=1000
    )
