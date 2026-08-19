from __future__ import annotations

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# ペアでダメな人同士のハード制約のためのモデル
class EmployeePairConstraint(Base):
    __tablename__ = "employee_pair_constraints"  # テーブル名の指定

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_a_id: Mapped[int] = mapped_column(
        ForeignKey("employee.id", ondelete="CASCADE"), nullable=False
    )
    employee_b_id: Mapped[int] = mapped_column(
        ForeignKey("employee.id", ondelete="CASCADE"), nullable=False
    )
