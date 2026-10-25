# 構成マップ（ファイルごとの役割）

リポジトリ全体を「どのファイルが何をしているか」で俯瞰するための地図。
詳細な逐行解説は [`docs/backend.md`](backend.md) / [`docs/frontend.md`](frontend.md)、
設計判断は [`docs/adr/`](adr/) を参照。

## 全体像

- **frontend/** … Vue 3 + TypeScript + Naive UI + Pinia（SPA）。
- **backend/** … FastAPI + SQLAlchemy 2 + Alembic。シフト生成は OR-tools CP-SAT、制約抽出は LLM。
- **deploy/** … GCP Cloud Run + Secret Manager の terraform、デプロイ手順。
- **docs/** … 要件・チュートリアル・ADR・本マップ。

---

## backend

### エントリ / 基盤（app/core, app/main.py）
- `app/main.py` … FastAPI アプリ生成、CORS、各ルーターの登録。`/api/health`。
- `app/core/config.py` … 環境変数設定(`Settings`)。DB・OAuth・LLM(anthropic/openai/deepseek/none)等。
- `app/core/database.py` … SQLAlchemy engine / `SessionLocal` / `get_db` / `Base`。
- `app/core/security.py` … パスワードハッシュ、JWT の発行・検証。
- `app/core/dates.py` … `month_range(year, month)`＝対象月の半開区間 [月初, 翌月初)（DRY共通化）。

### 認証（app/auth）
- `app/auth/deps.py` … `CurrentUser` / `AdminUser` 依存性（JWT からユーザー解決・権限チェック）。
- `app/auth/google.py` … Google OAuth（認可URL生成・コード交換・userinfo取得）。

### モデル（app/models）— DB テーブル定義
- `employee.py` … `Employee` / `EmployeeAvailability`（希望・不可・有給・確定出勤）。
- `shift.py` … `Shift` / `ShiftAssignment`（割当は shift/employee に ondelete=CASCADE）。
- `rule.py` … `ShiftPattern` / `HourlyStaffingRule`（時間別必要人数）。
- `user.py` … `User` / `AllowedLogin`（ログイン許可リスト。employee_id は SET NULL）。

### スキーマ（app/schemas）
- 各リソースの Pydantic 入出力モデル（`employee` / `shift` / `rule` / `payroll` / `auth` / `pair` / `notification`）。

### ルーター（app/routers）— API エンドポイント
- `shifts.py` … シフト取得 / **生成(LLM＋CP-SAT)** / 割当差し替え / 確定 / PDF・Excel 出力。
- `employees.py` … 従業員 CRUD、希望(availability)の一覧・登録・削除。
- `rules.py` … シフトパターン CRUD、時間別必要人数の取得・一括置換。
- `payroll.py` … 当月の人件費レポート取得。
- `pairs.py` … NGペア（同時勤務させない組）CRUD。
- `allowed_logins.py` … ログイン許可リスト CRUD（管理者のみ）。
- `auth.py` … Google ログイン・コールバック・`/me`（＋ローカル専用 dev-login）。
- `notifications.py` … ダッシュボード通知一覧。
- `dev.py` … 開発専用 seed / reset（本番は 404）。

### サービス（app/services）— 業務ロジック
- `shift_generation.py` … **シフト生成のオーケストレーション**。従業員・パターン・必要人数・希望・
  NGペア・LLM制約を集め、ソルバーを呼び、結果を保存して返す（ルーターはこれに委譲＝SRP）。
- `scheduler.py` … **CP-SAT スケジューラ**（`ShiftScheduler`）。必要人数・週回数・勤務可能時間帯・
  NGペア・LLM制約(全員休み/個別不可/週回数)を制約化し、3段フォールバックで解を返す。
- `llm.py` … 自然言語メモ → JSON 制約抽出。プロバイダは**戦略パターン**（`LlmProvider` /
  `resolve_provider`）で anthropic/openai/**deepseek**(OpenAI互換) を差し替え（OCP）。失敗時は空＋警告。
- `payroll.py` … 割当から人件費算出（深夜割増・交通費・有給・保険区分）。
- `staffing.py` … シフトパターン・時間別必要人数のデフォルト定義。
- `seeding.py` … `seed_defaults_if_missing(db)`＝既定マスタ投入（dev/seed_prod で共有・DRY）。
- `export.py` … シフト表の PDF / Excel 生成。
- `holidays.py` … 祝日・土日・繁忙日・day_category 判定。
- `notifications.py` … 通知の組み立て。

### スクリプト（backend/scripts）— 本番運用
- `seed_prod.py` … 本番にデモデータ投入（`@example.com` 目印）。
- `teardown_prod.py` … デモデータ削除（CASCADE で希望・割当も連鎖削除。`--yes` 必須）。
- `_prod_db.py` … 共通ヘルパー `db_host()`（接続先DBホスト表示・DRY）。

---

## frontend（src/）

### 基盤
- `App.vue` … テーマ(ライト/ダーク)・ロケール・起動ローディング・ヘッダー枠。
- `router/index.ts` … ルート定義、認証/管理者ガード、PC→マイページ自動遷移。
- `api/client.ts` … axios クライアント（baseURL・JWT 付与・タイムアウト）。
- `types/index.ts` … 全体の型定義。

### 状態管理（stores）— Pinia
- `auth.ts` … ログインユーザー(Me)の保持・復元(/auth/me)・ログアウト。
- `employee.ts` … 従業員 CRUD・希望(availability)・NGペア。
- `shift.ts` … シフト取得・生成・割当保存・人件費。
- `rule.ts` … シフトパターン・時間別必要人数。
- `theme.ts` … ライト/ダークの保持・適用・トグル。

### 共通化（utils / config / constants）※リファクタで新設
- `utils/date.ts` … `isoDate(d)`＝端末ローカルの `YYYY-MM-DD`。
- `utils/weekday.ts` … `weekdayColor(d)`（日=赤/土=青）、`dayCategory(d)`（平日/休日）。
- `utils/icon.ts` … `maskIconStyle(url)`＝マスク画像を currentColor で塗る style。
- `config/nav.ts` … ナビ項目 `navItems`（ヘッダー・ホームで共有）。
- `constants/availability.ts` … 希望種別ラベル `KIND_LABELS`（カレンダーと composable で共有）。

### composables（画面から分離した再利用ロジック）※SOLIDリファクタで新設
- `useShiftGrid.ts` … シフト表セルの表示(ラベル/時間帯バンド/有給)を計算し `cellAt`/`cellStyle` を返す。
- `useShortfalls.ts` … 人数不足(Shortfall)の算出。
- `useShiftGeneration.ts` … 生成(LLM＋ソルバー)の実行と入力状態・警告。
- `useAvailabilities.ts` … 希望のロード/追加/削除と「今後の同じ曜日へ一括適用」。

### 画面（views）
- `HomeView.vue` … スマホのホーム（ランチャータイル＋星トグル）。
- `DashboardView.vue` … マイページ（予定給与・通知）。
- `ShiftTableView.vue` … シフト表（管理者は生成/編集、従業員は閲覧のみ）。
- `RequestView.vue` … 希望提出（従業員は本人分、管理者は選択可）。
- `EmployeesView.vue` / `EmployeeCalendarView.vue` … 従業員管理・固定カレンダー。
- `RulesView.vue` … シフトパターン・必要人数の設定。
- `PayrollView.vue` … 人件費（表示項目のオンオフ可）。
- `LoginUsersView.vue` … ログイン管理（許可リスト）。
- `LoginView.vue` / `AuthCallbackView.vue` … ログイン・OAuth コールバック。
- `PrintPreviewView.vue` … 印刷プレビュー。

### コンポーネント（components）
- `HeaderBar.vue` … ヘッダー（左ドロワーのナビ＋星トグル、中央にページ名、右にユーザー）。
- `AvailabilityCalendar.vue` … 希望入力カレンダー（曜日一括＝登録後に同じ曜日へ適用）。
- `StarIcon.vue` … 星アイコン（`filled` で塗りつぶし。ダークON表示に使用・DRY）。
- `DevLoginTools.vue` … ローカル専用のログイン/モック投入ツール（本番バンドル除外）。
