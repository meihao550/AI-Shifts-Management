"""本番のデモデータ(email ...@example.com の従業員)を削除する。

従業員を削除すると、その希望(availabilities)とシフト割当(assignments)は
ondelete=CASCADE で自動削除される。users/allowed_logins の employee_id は
SET NULL（ログイン情報は消えずリンクだけ外れる）。
シフトパターン・必要人数(汎用マスタ)は残す。空になった Shift を消すなら --purge-empty-shifts。

安全のため、--yes を付けない限り「件数表示のみ（ドライラン）」で実削除しない。

使い方（本番 DATABASE_URL を渡す。backend/ から実行）:
  # 1) 件数確認（ドライラン）
  DATABASE_URL="$(gcloud secrets versions access latest --secret=database-url \
      --project=ai-shifts-ziyin-260930)" python scripts/teardown_prod.py
  # 2) 実削除
  DATABASE_URL="..." python scripts/teardown_prod.py --yes
  # 3) 空シフトも掃除
  DATABASE_URL="..." python scripts/teardown_prod.py --yes --purge-empty-shifts
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))  # backend/（app を import するため）
sys.path.insert(0, _HERE)  # scripts/（_prod_db を import するため）

from _prod_db import db_host  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.shift import Shift, ShiftAssignment  # noqa: E402

DEMO_DOMAIN = "@example.com"


def main() -> None:
    do_delete = "--yes" in sys.argv
    purge = "--purge-empty-shifts" in sys.argv
    print(f"接続先DBホスト: {db_host()}")
    db = SessionLocal()
    try:
        demo = (
            db.execute(select(Employee).where(Employee.email.like(f"%{DEMO_DOMAIN}")))
            .scalars()
            .all()
        )
        print(f"デモ従業員(削除対象): {len(demo)} 名")
        if not demo:
            print("削除対象なし。")
            return
        if not do_delete:
            print("※ ドライランです。実際に削除するには --yes を付けて再実行してください。")
            return

        # DB の ondelete=CASCADE により availabilities / shift_assignments も自動削除。
        db.execute(delete(Employee).where(Employee.email.like(f"%{DEMO_DOMAIN}")))
        db.commit()
        print(f"✔ デモ従業員 {len(demo)} 名を削除（希望・シフト割当も連鎖削除）")

        if purge:
            empty = (
                db.execute(
                    select(Shift.id).where(
                        ~select(ShiftAssignment.id)
                        .where(ShiftAssignment.shift_id == Shift.id)
                        .exists()
                    )
                )
                .scalars()
                .all()
            )
            if empty:
                db.execute(delete(Shift).where(Shift.id.in_(empty)))
                db.commit()
            print(f"✔ 空になったシフト {len(empty)} 件を削除")
    finally:
        db.close()


if __name__ == "__main__":
    main()
