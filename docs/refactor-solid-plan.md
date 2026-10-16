# SOLID リファクタリング計画（新セッションで実行する用）

目的: 大きい「神ファイル」を単一責務(SRP)に分割し、拡張に開き修正に閉じる(OCP/DIP)構造にする。
**挙動は変えない**。各ステップごとに検証: frontend `npm run build` / backend `uv run ruff check . && uv run pytest -q`（現状 43 passed）。
コミットは機能ごとに細分化・日本語・author=meihao550・**Co-Authored-By に Claude を含めない**。ブランチ `feat/expand-rows-all` に積み、ユーザーがPRマージ。

> usage 節約のため、**この計画は新しいセッションで** 実行すること（巨大な会話履歴を引き継がない）。1ステップずつ、検証→コミットで進める。

## 対象と優先度（上から着手）

### 1. backend: LLM プロバイダを戦略パターンに（OCP/DIP・低リスク・まず着手）
- 現状: `app/services/llm.py` の `derive_constraints_from_text` が `if provider == ...` の分岐で anthropic/openai/deepseek を直書き（新プロバイダ追加＝関数修正＝OCP違反）。
- 変更: `LlmProvider` プロトコル（`async def complete(system, user) -> str`）を定義し、`AnthropicProvider` / `OpenAICompatProvider`(openai・deepseek を base_url 違いで共有) を実装。`PROVIDERS: dict[str, factory]` のレジストリから解決。`derive_constraints_from_text` は「プロバイダ取得 → complete → _parse_json」だけに。
- 期待効果: 新プロバイダ追加はレジストリに1行。タイムアウト/リトライは各プロバイダに閉じる。
- 検証: 既存 `pytest`＋（任意）DeepSeek 実呼び出しスクリプト。

### 2. backend: シフト生成のドメイン処理をサービスへ（SRP/DIP）
- 現状: `app/routers/shifts.py` の `generate_shift` が HTTP 層なのに、EmployeeSpec/PatternSpec 構築・既定投入・ソルバー実行・永続化まで担う。
- 変更: `app/services/shift_generation.py` に `generate(db, payload) -> ShiftGenerateResult` を新設し、オーケストレーションを移動。ルーターは認可＋サービス呼び出しだけに。
- 検証: `pytest`（新規にサービス単体テストを1本追加できると良い）。

### 3. backend: `scheduler.py`(765行) を責務分割（SRP・最大の効果/要注意）
- 現状: `ShiftScheduler` が「ルックアップ(availability/mandatory/closed)」「変数生成」「各制約」「目的関数」「3段フォールバック」「結果抽出」を全部持つ。
- 変更（挙動不変・内部分割のみ）:
  - `scheduler/lookups.py` … `_unavailable_lookup`/`_preferred_lookup`/`_mandatory_lookup`/`_closed_dates` を純関数化。
  - `scheduler/constraints.py` … 「各制約を model に add する」純関数群（coverage/weekly/window/pairs/mandatory/unavailable/closed）。
  - `scheduler/objective.py` … 目的関数の組み立て。
  - `ShiftScheduler` は上記を呼ぶ**オーケストレータ**に縮小。公開IF(`solve()`)と結果型は不変。
- 検証: `tests/test_scheduler.py`（休業日テスト含む）を**各分割後に必ず緑**にする。リスク高なので小刻みにコミット。

### 4. frontend: `ShiftTableView.vue`(785行) をコンポーザブル＋子コンポーネントに（SRP）
- 変更: `composables/useShiftGrid.ts`（cellMap/draft/セル編集）、`composables/useShiftGeneration.ts`（生成・警告）、`composables/useShortfalls.ts`（人数不足計算）に抽出。表描画は `components/ShiftGrid.vue`、生成UIは `components/GeneratePanel.vue` に分離。親は組み立てだけ。
- 検証: `npm run build`＋画面スモーク（管理者=生成/編集、従業員=閲覧のみ）。

### 5. frontend: `AvailabilityCalendar.vue`(521行) の希望CRUD/曜日一括を composable 化（SRP）
- `composables/useAvailabilities.ts` に抽出。表示コンポーネントは描画に専念。

## 進め方（usage 最適）
1. 新セッションを開き、このファイルと `docs/architecture.md` だけ読む。
2. 上から1項目ずつ: 変更 → `build`/`ruff`/`pytest` → 1コミット。無関係ファイルは触らない。
3. 迷ったら「公開IF(関数シグネチャ/APIルート/画面挙動)は不変」を最優先に。
4. リスク順は 1 → 2 → 4 → 5 → 3（3 のソルバー分割は最後に慎重に）。
