# AI-Shifts-Management

勤務シフトの自動生成と人件費計算を行うシステムの用語集（ドメイン語彙）。

## Language

### シフト (Scheduling)

**シフトパターン (Shift Pattern)**:
勤務枠の再利用テンプレート。開始・終了・休憩・区分を持つ雛形であり、具体的な割当ではない。
_Avoid_: シフト（パターンと割当のどちらか曖昧）

**割当 (Assignment)**:
「ある従業員 × ある日 × ひとつの勤務」の具体インスタンス。生成元のパターンとは別物。
_Avoid_: シフト（曖昧）

**メインシフト (Main Shift)** — _廃止 (deprecated)_:
かつては従業員が主に入る区分（朝/夜/深夜）を指し、ピン留めでハード制約になった。配置制御は **勤務可能時間帯** に一本化され、この語彙は使わない（[ADR-0002](docs/adr/0002-main-shift-category-to-availability-window.md)）。

**勤務可能時間帯 (Availability Window)**:
従業員が普段入れる時間帯を1時間単位で表す窓（`available_start_hour`〜`available_end_hour`）。設定するとハード制約になり、**窓に完全に収まるパターンにのみ**配置できる。未設定なら無制限。どのパターンに配置してよいかを制御する唯一の仕組み。

**週シフト回数 (Weekly Shift Count)**:
従業員が1週間（日曜起点）に入る割当の回数（`weekly_shifts`）。`weekly_shifts_pinned` が真の従業員は、完全な7日週で「ちょうどこの回数」を守るハード制約になる（半端な週はソフト按分）。必要人数と競合する週は、過剰配置を避けるため週回数を先にソフトへ落とす（[ADR-0003](docs/adr/0003-weekly-shift-count-hard-constraint.md)）。
_Avoid_: メインシフト（廃止語）

**許容過剰 (Surplus Tolerance, α)**:
各時間に必要人数を超えて配置してよい上限（α）。`必要人数 ≤ 配置 ≤ 必要人数 + α`。短い勤務可能時間帯の従業員なども +α の枠で配置できる。既定 α=1（[ADR-0005](docs/adr/0005-coverage-surplus-tolerance.md)）。

**連勤制限 (Consecutive Work-day Limit)**:
全従業員一律で連続勤務は最大4日（5連勤以上を禁止）。生成月内の連続日でカウントし、月をまたぐ連続は数えない（[ADR-0008](docs/adr/0008-consecutive-work-day-limit.md)）。

**Wワークパターン (Dual-work Pattern)** — _廃止 (deprecated)_:
かつては `is_basic=false` の掛け持ち専用パターンを指した。基本/Wワークのパターン区別は撤廃され、全パターンは1つのプールに統合された。配置制限は **勤務可能時間帯** のみ（[ADR-0004](docs/adr/0004-unify-shift-patterns.md)）。

**Wワーク従業員 (Dual Worker)**:
掛け持ち（複数の職を持つ）従業員の目印（`is_dual_worker`）。現在はシフト生成の配置には影響しない属性ラベル。

**固定カレンダー (Fixed Calendar)**:
従業員管理の「カレンダー」は、シフト表の「休日・希望日」カレンダーと**同一コンポーネント・同一データ**（`EmployeeAvailability`）を従業員固定で表示したもの。編集は即同期する。毎月同じ曜日パターン（例: 木曜だけ確定出勤・他は休日）は「**曜日で一括登録**」で当月へ適用して流用する（[ADR-0007](docs/adr/0007-fixed-weekly-calendar.md)）。

**確定出勤 (Mandatory Work)**:
availability 種別 `mandatory`。その日は必ず1シフト入れる（通常段はハード、診断段は強いソフト＋警告）。開始・終了を1時間単位で指定でき（`note` "HH:MM-HH:MM"）、指定時はその窓に収まるパターンで配置する。希望日(`preferred`)＝出勤ソフト（弱い希望）と区別する（[ADR-0009](docs/adr/0009-mandatory-fixed-work.md)）。

### 勤務時間 (Working Time)

**総スパン (Gross Span)**:
割当の素の時計上の長さ（終了 − 開始）。休憩を引かない値。API では `total_hours`。
_Avoid_: 労働時間（実働の意味に取られる）

**実働時間 (Worked Hours)**:
賃金・保険判定の基礎となる時間 = 総スパン − 休憩。API では `worked_hours`。
_Avoid_: 労働時間（曖昧）、単なる「実働」

**休憩 (Break)**:
シフト内の無給の休憩。分単位で保持（`rest_minutes`）。賃金は発生せず、実働時間から除外される。UI では1時間刻みで入力する。
_Avoid_: 休息

**深夜割増 (Overnight Premium)**:
22:00–05:00 帯に働いた時間に対する 25% の割増賃金。

### 給与 (Payroll)

**人件費 (Labor Cost)**:
従業員1人・1か月あたりの 基本給 + 深夜割増 + 交通費 + 有給 の合計。

**保険区分 (Insurance Type)**:
`social` / `employment` / `none`。従業員ごとに管理者が設定する**マスタ属性**（`insurance_type`）。シフト生成で月間実働時間をハードに制約する: 社保 ≥120h / 雇用 80〜119h / なし ≤79h（[ADR-0006](docs/adr/0006-insurance-monthly-hours.md)）。人件費表示もこのマスタ属性を用いる（未設定時のみ実働時間から推定）。

**有給 (Paid Leave)**:
勤務しない日だが人件費に日額を加算する。実働時間・保険判定には算入しない。
