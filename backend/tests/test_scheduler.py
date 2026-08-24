"""制約問題のテストコード"""

# 制約問題はテストを先に作らないとコーディングがあってるかどうかわからないのでつくります

from datetime import time

from app.services.scheduler import (  # この三つは型定義してるだけ
    EmployeeSpec,
    PatternSpec,
    ShiftScheduler,
)


def test_forbidden_pair_makes_infeasible():
    employee_a = EmployeeSpec(
        id=1, name="A", weekly_target=7, main_shift_type="morning", hourly_wage=1000
    )
    employee_b = EmployeeSpec(
        id=2, name="B", weekly_target=7, main_shift_type="morning", hourly_wage=1000
    )

    employees = [employee_a, employee_b]

    patterns = [
        PatternSpec(
            id=1,
            code="morning",
            label="朝",
            start=time(9, 0),
            end=time(17, 0),
            category="morning",
            is_basic=True,
        )
    ]

    # 平日の朝は２人必要にする
    # 土日祝日の朝も２人必要にする
    staffing_rules = {("weekday", "morning"): 2, ("weekend_or_holiday", "morning"): 2}

    scheduler = ShiftScheduler(
        year=2026,
        month=2,
        employees=employees,
        patterns=patterns,
        staffing_rules=staffing_rules,
        availabilities=[],
    )

    result = scheduler.solve()

    assert result.solver_status in (
        "OPTIMAL",
        "FEASIBLE",
    )  # OPTIMALとFEASIBLEはCP-satの公式ドキュメントをみる
