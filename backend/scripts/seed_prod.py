"""本番にデモデータを投入する（すぐ消せるよう email=...@example.com を目印にする）。

デモ内容: 「デモ従業員01..25 / email emp01..25@example.com」＋（無ければ）
シフトパターン・時間別必要人数のデフォルト。生成に必要な最低限を揃える。
削除は scripts/teardown_prod.py（@example.com の従業員を消すと希望・割当も連鎖削除）。

使い方（本番 DATABASE_URL を渡す。backend/ から実行）:
  DATABASE_URL="$(gcloud secrets versions access latest --secret=database-url \
      --project=ai-shifts-ziyin-260930)" python scripts/seed_prod.py
"""

from __future__ import annotations

import os
import sys
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.rule import HourlyStaffingRule, ShiftPattern  # noqa: E402
from app.services.staffing import default_hourly_rules, default_patterns  # noqa: E402

DEMO_DOMAIN = "@example.com"  # この email ドメインの従業員＝デモデータの目印


def _db_host() -> str:
    try:
        url = get_settings().database_url.replace("postgresql+psycopg", "postgresql")
        return urlsplit(url).hostname or "?"
    except Exception:
        return "?"


def main() -> None:
    print(f"接続先DBホスト: {_db_host()}")
    db = SessionLocal()
    try:
        # 生成に必須のマスタ（無ければデフォルト投入）。汎用設定なので残しても害なし。
        if not db.execute(select(ShiftPattern)).first():
            db.add_all([ShiftPattern(**p) for p in default_patterns()])
            print("＋ シフトパターン(デフォルト) を投入")
        if not db.execute(select(HourlyStaffingRule)).first():
            db.add_all([HourlyStaffingRule(**r) for r in default_hourly_rules()])
            print("＋ 時間別必要人数(デフォルト) を投入")

        # デモ従業員（既にあれば二重投入しない）
        exists = db.execute(
            select(Employee.id).where(Employee.email.like(f"%{DEMO_DOMAIN}"))
        ).first()
        if exists:
            print("デモ従業員は既に存在するためスキップ")
        else:
            db.add_all(
                [
                    Employee(
                        name=f"デモ従業員{i:02d}",
                        email=f"emp{i:02d}{DEMO_DOMAIN}",
                        age=25 + (i % 15),
                        transport_cost=500,
                        hourly_wage=1200,
                        weekly_shifts=3 + (i % 3),
                        is_dual_worker=(i % 5 == 0),
                    )
                    for i in range(1, 26)
                ]
            )
            print("＋ デモ従業員 25 名 を投入 (emp01..25@example.com)")

        db.commit()
        total = (
            db.execute(select(Employee).where(Employee.email.like(f"%{DEMO_DOMAIN}")))
            .scalars()
            .all()
        )
        print(f"完了。現在のデモ従業員数 = {len(total)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
