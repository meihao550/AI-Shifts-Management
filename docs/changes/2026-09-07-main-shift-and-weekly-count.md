# 実装記録: メインシフト廃止・週回数ハード制約化 (2026-09-07)

ブランチ `fix/shift-output`。関連決定は [ADR-0002](../adr/0002-main-shift-category-to-availability-window.md) と
[ADR-0003](../adr/0003-weekly-shift-count-hard-constraint.md)、語彙は [CONTEXT.md](../../CONTEXT.md) を参照。

## 背景（要望）

1. 「メイン区分のみON」をデフォルトにしたい → グリルの結果、3区分(朝/夜/深夜)固定は
   粒度が粗く「朝固定」問題があるため廃止し、既存の**勤務可能時間帯(1時間窓)**に一本化。
2. シフト生成で「週に2回入りたい人は絶対2回」入れたい → 週回数を**週単位・ちょうどN回・ハード制約**に。

## ① メインシフト区分の廃止（ADR-0002）

配置制御を `available_start_hour`/`available_end_hour`（1時間窓・ハード、窓に完全に収まる
パターンのみ配置可）に一本化し、`main_shift_type`/`main_shift_pinned` を廃止した。

- `backend/app/services/scheduler.py`
  - `EmployeeSpec` から `main_shift_type`/`main_shift_pinned` を削除。
  - ピン留めハード制約・メインシフト寄せ(ソフト)ロジックは**削除せずコメントアウト**し、
    廃止理由(ADR-0002)を明記（挙動の由来を追えるようにするため）。
- `backend/app/models/employee.py` / `backend/app/schemas/employee.py`: 2カラムを削除。
- `backend/app/routers/shifts.py` / `backend/app/routers/dev.py`: 該当引数を削除。
- `frontend/src/types/index.ts`: `Employee` から2フィールド削除。
- `frontend/src/views/EmployeesView.vue`: メインシフト/ピンの列・フォーム・`shiftOptions` を削除。
- `frontend/src/views/ShiftTableView.vue`: メイン不一致ハイライト(`mainMismatch`)・
  `shiftTypeLabel`・`.cell-main-mismatch` CSS を削除。

## ② 週回数を週単位ハード制約化（ADR-0003）

- 新フラグ `weekly_shifts_pinned`（`employee.py` モデル / スキーマ / `EmployeeSpec` / TS型 / UI）。
  **新規従業員はデフォルトON**、既存従業員はOFFのまま（マイグレーションで一括ONにしない）。
- `scheduler.py` の週回数制約を**月合計ソフト → 週単位**に作り替え:
  - `weekly_shifts_pinned` かつ**完全な7日週**は `週合計 == weekly` のハード。
  - 月末月初の**半端な週**は `round(weekly × 日数/7)` を目標にした按分**ソフト**。
  - 非pinnedは常にソフト。
- `solve()` を**3段フォールバック**に変更（必ず部分解を返す）。過剰配置を出さないことを
  優先し、競合時は週回数を先に緩める（当初は週回数優先だったが、供給過多で過剰配置が
  多発したため見直し。ADR-0003 の Considered Options 参照）:
  1. 週回数(完全週=ちょうど) ＋ 必要人数(==) を両方ハード。
  2. 解けなければ**必要人数(==)は維持**し週回数をソフトに降格（供給過多の週は各人が自然に
     減り、過剰配置ゼロ）。「◯◯さんは週N回入れませんでした」を警告。
  3. なお不可（真の人手不足）なら必要人数をスラック化。「◯日◯時：△人不足」を警告。

## マイグレーション

機能ごとに2本に分割（コミットも機能単位）。現行head `b2c3d4e5f6a7` に続けて:

1. `e1d2c3b4a5f6_drop_main_shift_columns.py`（ADR-0002）: `main_shift_pinned` /
   `main_shift_type` を削除。
2. `a9b8c7d6e5f4_add_weekly_shifts_pinned.py`（ADR-0003）: `weekly_shifts_pinned` を追加。
   **`server_default=false` で既存行はOFF**にバックフィル（新規のORM INSERTはモデルの
   `default=True` によりON）。

適用: `alembic upgrade head`（DBへの適用は未実施。手動で実行のこと）。

## 検証

- backend: `pytest` 全27件パス（`test_scheduler.py` に週回数ハードのテストを追加、
  メインピンの旧テストを置換）。`ruff check` パス。`alembic heads` 単一head。
- frontend: `vue-tsc --noEmit` パス。

## 未実施・注意

- マイグレーションのDB適用（`alembic upgrade head`）は本人が実行。
- 全員デフォルトONのため、供給次第で必要人数の不足警告が出やすくなる。部分解を手動修正する運用前提。
