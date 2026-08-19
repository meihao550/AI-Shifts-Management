from datetime import date
from types import SimpleNamespace

from app.services.notifications import _next_month


# db.execute(...).scalar_one_or_none() がshiftを返すテスト
def _fake_db(shift):
    result = SimpleNamespace(scalar_one_or_none=lambda: shift)
    return SimpleNamespace(execute=lambda stmt: result)


# uv run pytestで実行可能。8月26日以降は9月が出るのかどうかを確かめてる（通知のやつ）
def test_next_month_normal():
    assert _next_month(date(2026, 8, 26)) == (2026, 9)
