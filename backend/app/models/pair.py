# この__future__がないと、実行できなくなる可能性がある。
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# ペアでダメな人同士のハード制約のためのモデル
class EmployeePairConstraint(Base):
    __tablename__ = "employee_pair_constraints"  # テーブル名の指定

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employees_a_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    employees_b_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
