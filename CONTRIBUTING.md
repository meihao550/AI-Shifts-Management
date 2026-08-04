# CONTRIBUTING — 開発ガイドライン

このドキュメントは AI-Shifts-Management に **コミット/PR を送る前** に必ず一読してください。
チーム内の環境差・レビューコスト・本番事故を減らすためのルールをまとめています。

---

## 目次

1. [開発環境](#1-開発環境)
2. [ブランチ運用](#2-ブランチ運用)
3. [コミットメッセージ](#3-コミットメッセージ)
4. [プルリクエスト](#4-プルリクエスト)
5. [コードスタイル](#5-コードスタイル)
6. [テスト](#6-テスト)
7. [DB マイグレーション](#7-db-マイグレーション)
8. [秘密情報の扱い](#8-秘密情報の扱い)
9. [レビュー観点](#9-レビュー観点)

---

## 1. 開発環境

**Dev Container が唯一の推奨環境です。** 各自ローカルに Python/Node を直接入れる方法は環境差の温床になるため推奨しません。

```
必須: VS Code + Docker Desktop + Dev Containers 拡張
```

`.python-version` (3.11)、`.nvmrc` (Node 20)、`.editorconfig` を尊重してください。ローカル IDE 設定が違うと lint/format 差分が出て PR が汚れます。

---

## 2. ブランチ運用

### 保護ブランチ

- `main`: 常にデプロイ可能な状態。直接 push 禁止。PR + review + CI green 必須。

### 作業ブランチ

以下の prefix を使ってください：

| Prefix | 用途 |
|---|---|
| `feat/xxx` | 新機能 |
| `fix/xxx` | バグ修正 |
| `docs/xxx` | ドキュメント |
| `refactor/xxx` | 挙動を変えないリファクタ |
| `chore/xxx` | 依存更新・設定変更など |
| `test/xxx` | テスト追加 |

例: `feat/employee-search-api`

### 派生元

常に **最新の `origin/main` から切ります**：

```bash
git fetch origin
git checkout -b feat/xxx origin/main
```

古い main から派生してレビュー中に競合が起きると全員が消耗します。

---

## 3. コミットメッセージ

**Conventional Commits** に従います：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### type

- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント
- `style`: 見た目のみ（挙動変わらず）
- `refactor`: 挙動を変えない書き換え
- `test`: テスト追加/修正
- `chore`: 設定・依存・スクリプト

### scope

`backend` / `frontend` / `deploy` / `docs` / `ci` / `db` など。

### subject

- 命令形・現在形（`add xxx`, `fix xxx`）
- 50 文字以内
- 末尾にピリオド不要
- 日本語 or 英語どちらでも可（プロジェクト内で統一）

### 例

```
feat(backend): 従業員検索 API を追加
fix(frontend): シフト表の日付が UTC ずれする問題を修正
docs(deploy): Supabase セットアップ手順を追加
chore(ci): pre-commit を GitHub Actions で実行
```

### 悪い例

```
更新                        ← 何を？
fix bug                     ← どのバグ？
WIP                         ← merge しないで
Update README.md            ← どこを何のために？
```

---

## 4. プルリクエスト

### PR タイトル

コミットメッセージと同じフォーマット。

### PR 本文テンプレート

```markdown
## 概要
<何を・なぜ>

## 変更点
- ...
- ...

## テスト方法
- [ ] `cd backend && uv run pytest`
- [ ] Dev Container で手動確認: シフト生成 → 人件費表示

## スクリーンショット / 動画
<UI 変更があれば>

## 影響範囲
<DB migration / 環境変数 / 依存追加 などあれば明記>

## 関連 Issue
Closes #xx
```

### レビュー依頼前チェックリスト

- [ ] CI が green
- [ ] `uv run ruff check` / `npm run lint` がクリーン
- [ ] `uv run mypy app` がクリーン
- [ ] 新機能ならテストを追加
- [ ] DB スキーマ変更したら Alembic マイグレーション追加
- [ ] `.env.example` に新しい環境変数を追記
- [ ] README / DEPLOY.md / TUTORIAL.md の記述を必要に応じて更新

### マージ方式

- **Squash merge** をデフォルトに（履歴が綺麗）
- Squash 時の commit message も Conventional Commits で

---

## 5. コードスタイル

### バックエンド (Python)

- **Ruff** で lint + format
- **mypy** で型チェック（strict モードではないが `Any` は極力避ける）
- 関数・変数は snake_case、クラスは PascalCase
- 型注釈は必須（`-> None` も書く）
- 例外は極力具体的なクラスで catch（`except Exception:` は避ける）

```python
# OK
def calculate_hours(assignments: list[ShiftAssignment]) -> float:
    return sum(_duration(a) for a in assignments)

# NG (型注釈なし、Any を隠蔽)
def calculate_hours(assignments):
    ...
```

### フロント (Vue / TS)

- **ESLint + Prettier** で lint + format
- コンポーネントは PascalCase (`EmployeeCard.vue`)、変数は camelCase
- `<script setup lang="ts">` のみ使用（Options API は使わない）
- `any` は原則禁止、`unknown` を使う
- Composables (`use*`) と Store (`use*Store`) の命名を守る

### ファイル配置

- API 呼び出しは `src/api/`
- 状態管理は `src/stores/`
- 純粋な UI 部品は `src/components/`
- 画面全体は `src/views/`
- 型定義は `src/types/`

---

## 6. テスト

### 変更したら必ずテストを書く/更新する

- **バックエンド**: `backend/tests/test_*.py`（Pytest）
- **フロント**: `frontend/src/**/__tests__/*.spec.ts`（Vitest）

### ハッピーパスとエッジケース

- 正常系だけでなく、境界値・失敗系も 1 ケースは書く
- 例：`test_calculate_payroll_insurance_thresholds`（80h/120h の境界確認）

### 統合テストと単体テスト

- 単体で守れる範囲（純関数）は単体テスト
- ルーターは統合テスト（`httpx.AsyncClient` + `TestClient`）を検討

---

## 7. DB マイグレーション

### 手順

```bash
# 1. モデルを編集
vim backend/app/models/employee.py

# 2. マイグレーション生成
cd backend
uv run alembic revision --autogenerate -m "add hourly_wage column"

# 3. 生成された alembic/versions/xxxx_...py を確認・手直し
#    * autogenerate は完璧ではないので目視レビュー必須
#    * 特に「テーブル rename」「NULL 制約変更」「デフォルト値」

# 4. ローカル DB に適用
uv run alembic upgrade head

# 5. アプリ動作確認
```

### 注意

- **本番の DB を直接触らない**（毎回マイグレーション経由）
- ロールバック不可能な変更は PR で明記
- 大きなテーブルへの ALTER は Cloud SQL 停止時間の考慮が必要（本番投入時）

---

## 8. 秘密情報の扱い

### **絶対に commit してはいけないもの**

- `.env`（`.env.example` は OK）
- API キー、パスワード、証明書
- `deploy/terraform/terraform.tfvars`（`.example` は OK）
- Service Account の JSON

### 誤 commit したら

1. **即 Slack で報告**
2. 該当キー / 認証情報を即座に revoke（Anthropic / OpenAI / Google Cloud で新規発行）
3. `git filter-repo` で履歴から除去（reviewer と相談）
4. `git push --force`（保護ブランチ以外）

事故ってからでは遅いので、**ステージング前に `git diff --cached` で確認する癖**をつけてください。

### pre-commit で防止

```bash
pip install pre-commit
pre-commit install
```

これで commit 時に自動 lint + シークレット疑いスキャンが走ります。

---

## 9. レビュー観点

reviewer が見るポイント（reviewer もこれをチェックリストにしてください）：

### 機能

- [ ] 期待通り動作する
- [ ] エッジケースが考慮されている（空データ / 大量データ / 権限外アクセス）
- [ ] 既存機能を壊していない

### コード品質

- [ ] 命名が説明的
- [ ] 関数が長すぎない（目安: 40 行）
- [ ] 責務が明確（1 関数 1 目的）
- [ ] コメントが「what」ではなく「why」を書いている

### セキュリティ

- [ ] 権限チェック（`AdminUser` / `CurrentUser`）が入っている
- [ ] SQL Injection の余地なし（SQLAlchemy 標準 API を使っている）
- [ ] XSS 対策（Vue のテンプレートはデフォルトで OK、`v-html` 使用時は要注意）
- [ ] 秘密情報が漏れていない

### パフォーマンス

- [ ] N+1 クエリになっていない（`selectinload` などで一括ロード）
- [ ] フロントのバンドルサイズが極端に増えていない

### テスト

- [ ] 追加された分のテストがある
- [ ] `pytest` / `vitest` が通っている

---

## 質問・提案

- 使いにくいルールがあれば PR を送るか issue で議論
- 「これって守るべき？」と迷ったら reviewer に聞いて OK

チーム開発の質はプロセスで決まります。快適にコード書ける環境をみんなで作りましょう。
