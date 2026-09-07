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

**Wワークパターン (Dual-work Pattern)**:
`is_basic=false` のパターン。掛け持ち従業員(dual worker)のみ配置可。基本パターンは全員に配置可。
例外: **勤務可能時間帯** を持つ通常従業員で、窓に収まる基本パターンが1つも無い場合は、窓に収まるWワークパターンにも配置できる（そうしないと1枠も入れないため）。

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

**保険区分 (Insurance Status)**:
`social` / `employment` / `none`。月間の実働時間で判定（≥120h / ≥80h / それ未満）。

**有給 (Paid Leave)**:
勤務しない日だが人件費に日額を加算する。実働時間・保険判定には算入しない。
