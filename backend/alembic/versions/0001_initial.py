"""initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("age", sa.Integer, nullable=True),
        sa.Column("transport_cost", sa.Integer, nullable=False, server_default="0"),
        sa.Column("hourly_wage", sa.Integer, nullable=False, server_default="1100"),
        sa.Column("main_shift_type", sa.String(32), nullable=True),
        sa.Column("weekly_shifts", sa.Integer, nullable=False, server_default="3"),
        sa.Column(
            "role",
            sa.Enum("admin", "employee", name="employee_role"),
            nullable=False,
            server_default="employee",
        ),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("picture_url", sa.String(500), nullable=True),
        sa.Column(
            "role",
            sa.Enum("admin", "employee", name="user_role"),
            nullable=False,
            server_default="employee",
        ),
        sa.Column("google_sub", sa.String(64), unique=True, nullable=True),
        sa.Column(
            "employee_id",
            sa.Integer,
            sa.ForeignKey("employees.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "employee_availabilities",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "employee_id",
            sa.Integer,
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_date", sa.Date, nullable=False),
        sa.Column("shift_type", sa.String(32), nullable=True),
        sa.Column(
            "kind",
            sa.Enum("unavailable", "preferred", name="availability_kind"),
            nullable=False,
        ),
        sa.Column("note", sa.String(255), nullable=True),
        sa.UniqueConstraint("employee_id", "target_date", "shift_type", "kind", name="uq_availability"),
    )

    op.create_table(
        "shift_patterns",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("is_basic", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("category", sa.String(16), nullable=False),
        sa.UniqueConstraint("code", name="uq_shift_pattern_code"),
    )

    op.create_table(
        "staffing_rules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "day_category",
            sa.Enum("weekday", "weekend_or_holiday", name="day_category"),
            nullable=False,
        ),
        sa.Column("shift_category", sa.String(16), nullable=False),
        sa.Column("required", sa.Integer, nullable=False),
        sa.UniqueConstraint("day_category", "shift_category", name="uq_staffing_rule"),
    )

    op.create_table(
        "shifts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("month", sa.Integer, nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "published", "finalized", name="shift_status"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("year", "month", name="uq_shift_month"),
    )

    op.create_table(
        "shift_assignments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "shift_id",
            sa.Integer,
            sa.ForeignKey("shifts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            sa.Integer,
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_date", sa.Date, nullable=False),
        sa.Column("shift_type", sa.String(32), nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("crosses_midnight", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint(
            "shift_id", "target_date", "employee_id", "start_time", name="uq_assignment"
        ),
    )


def downgrade() -> None:
    op.drop_table("shift_assignments")
    op.drop_table("shifts")
    op.drop_table("staffing_rules")
    op.drop_table("shift_patterns")
    op.drop_table("employee_availabilities")
    op.drop_table("users")
    op.drop_table("employees")
    op.execute("DROP TYPE IF EXISTS shift_status")
    op.execute("DROP TYPE IF EXISTS day_category")
    op.execute("DROP TYPE IF EXISTS availability_kind")
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP TYPE IF EXISTS employee_role")
