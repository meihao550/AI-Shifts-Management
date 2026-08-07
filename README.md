# AI-Shifts-Management

生成 AI（LLM）と OR-tools CP-SAT による制約プログラミングを組み合わせた、シフト自動作成 / 人件費計算 Web アプリです。

- **本番環境**: AWSで構築する。
- **企画書**: [`docs/Project.pdf`](docs/project-requirements-ver1.1.md)
- **チュートリアル（初心者向け）**: [`docs/TUTORIAL.md`](docs/TUTORIAL.md)
- **デプロイ手順**: [`deploy/DEPLOY.md`](deploy/DEPLOY.md)
- **開発ルール**: [`CONTRIBUTING.md`](CONTRIBUTING.md)

---

## 機能

| ID | 機能 | 概要 |
|---|---|---|
| F-1 | AI シフト自動生成 | LLM が自然言語の追加事情（イベント、有休など）を JSON 制約に変換し、CP-SAT が全体最適化してシフトを出力 |
| F-2 | 人件費自動計算 | 深夜割増を含む人件費計算、月間労働時間に応じた社会保険/雇用保険の適用判定 |
| F-3 | 従業員管理 | 名前・年齢・交通費・時給・週勤務回数などの管理 |
| F-4 | ルール設定 | 曜日別必要人員数、シフトパターンの設定 |
| F-5 | PDF / Excel 出力 | 印刷プレビュー画面から出力 |
| F-6 | 認証 | Google Workspace OAuth（管理者/一般ロール） |

---

## アーキテクチャ

```
┌────────────┐   HTTPS   ┌──────────────┐          ┌──────────────┐
│ ブラウザ   │ ────────▶ │ Cloud Run    │  psycopg │ Supabase     │
│ (Vue 3)    │           │ (FastAPI)    │ ───────▶ │ PostgreSQL   │
└────────────┘           └──────┬───────┘          └──────────────┘
                                │
                                │ HTTPS
                                ▼
                    ┌─────────────────────┐
                    │ Anthropic / OpenAI  │
                    │ (LLM API)           │
                    └─────────────────────┘
```

---

## 技術スタック

| レイヤ | 技術 | 選定理由 |
|---|---|---|
| **フロント** | Vue 3 + TypeScript + Vite | リアクティブな表 UI に強い / 型安全 / ビルドが速い |
| 状態管理 | Pinia | Vue 公式、Composition API と親和性が高い |
| UI ライブラリ | Naive UI | 表 / カレンダーが揃っていて日本語対応 |
| **バックエンド** | FastAPI + Pydantic v2 | OpenAPI 自動生成、型検証、非同期対応 |
| ORM | SQLAlchemy 2 + Alembic | Python 標準、マイグレーション自動化 |
| **DB** | PostgreSQL 16（Supabase） | Free 枠で運用可、SQL 標準 |
| **最適化** | OR-tools CP-SAT | シフトスケジューリング問題向け国産級ソルバ |
| **LLM** | Anthropic Claude または OpenAI | `.env` で切替、自然言語 → JSON 制約変換 |
| **認証** | Google OAuth 2.0 + JWT | Workspace ドメインで絞り込み可能 |
| **開発環境** | Dev Container (VS Code) | Python / Node / Terraform / gcloud すべて統一 |
| **CI / Lint** | Ruff + mypy + ESLint + Prettier + Vitest + Pytest | 自動整形と型検証 |
| **デプロイ** | AWS + Terraform | サーバレスで無料枠内、コード管理化 |

---

## クイックスタート（Dev Container）

**チームで環境差ゼロにするため、Dev Container を推奨します。**

### 必要なもの

- [VS Code](https://code.visualstudio.com/)
- [Dev Containers 拡張](vscode:extension/ms-vscode-remote.remote-containers)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)（起動しておく）

### 手順

1. リポジトリを clone してVS Code で開く
   ```bash
   git clone https://github.com/meihao550/AI-Shifts-Management.git
   code AI-Shifts-Management
   ```
2. VS Code の右下に「Reopen in Container」通知が出るのでクリック
   （出ない場合は `Cmd+Shift+P` → **Dev Containers: Reopen in Container**）
3. 初回はコンテナビルドで 5〜10 分。完了後、ターミナルはコンテナ内に接続されます
4. 起動：
   ```bash
   bash dev.sh
   ```
5. ブラウザで http://localhost:5173 を開く

**DB は Dev Container の `db` サービスとして自動起動**するので、追加の設定なしで動きます。

---

## 環境変数

- **開発**: `.env.example` をコピーして `.env` を作成し、必要に応じて編集
- **本番**: `deploy/DEPLOY.md` を参照

`.env` に書く主な項目：

| 変数 | 用途 | 例 |
|---|---|---|
| `SECRET_KEY` | JWT 署名鍵 | `openssl rand -hex 32` で生成 |
| `DATABASE_URL` | Postgres 接続 | `postgresql+psycopg://shifts:shifts_password@db:5432/shifts_db` |
| `GOOGLE_CLIENT_ID` | OAuth | Cloud Console で発行 |
| `GOOGLE_CLIENT_SECRET` | OAuth | 同上 |
| `LLM_PROVIDER` | LLM 切替 | `anthropic` / `openai` |
| `ANTHROPIC_API_KEY` | Claude 用 | https://console.anthropic.com/ |
| `OPENAI_API_KEY` | OpenAI 用 | https://platform.openai.com/ |

---

## 開発コマンド

```bash
# ─── バックエンド ───
cd backend
uv run pytest                    # テスト
uv run ruff check .              # Lint
uv run ruff format .             # Format
uv run mypy app                  # 型チェック
uv run alembic upgrade head      # マイグレーション適用
uv run alembic revision --autogenerate -m "message"  # マイグレーション生成

# ─── フロントエンド ───
cd frontend
npm run test:unit                # テスト
npm run lint                     # Lint + Fix
npm run format                   # Prettier 整形
npm run build                    # 本番ビルド (型チェック含む)
```

### pre-commit フック（推奨）

コミット前に自動で lint/format が走ります。

```bash
pip install pre-commit
pre-commit install
```

---

## テスト

```bash
# backend
cd backend && uv run pytest

# frontend
cd frontend && npm run test:unit
```

---

## デプロイ

本番デプロイの詳細手順は [`deploy/DEPLOY.md`](deploy/DEPLOY.md) を参照。

- **推奨構成**: Supabase (Postgres) + Cloud Run (backend / frontend) — **月額 ¥0**（無料枠内）
- 予算アラート ¥100/月 で自動通知（Cloud Billing）

---

## ディレクトリ構成

```
AI-Shifts-Management/
├── .devcontainer/    Dev Container 定義（VS Code）
├── .github/          GitHub Actions ワークフロー
├── backend/          FastAPI + CP-SAT
│   ├── app/
│   │   ├── auth/     Google OAuth + JWT
│   │   ├── core/     設定・DB接続
│   │   ├── models/   SQLAlchemy モデル
│   │   ├── schemas/  Pydantic スキーマ
│   │   ├── routers/  API エンドポイント
│   │   └── services/ CP-SAT / LLM / 人件費 / 出力
│   ├── alembic/      DB マイグレーション
│   └── tests/
├── frontend/         Vue3 + Naive UI
│   └── src/
│       ├── api/      APIクライアント
│       ├── router/   Vue Router
│       ├── stores/   Pinia
│       ├── views/    画面
│       └── components/
├── deploy/
│   ├── DEPLOY.md     デプロイ手順書
│   └── terraform/    Cloud Run + Secret Manager
├── docs/
│   ├── Project.pdf   企画書
│   └── TUTORIAL.md   初心者向けチュートリアル
├── docker-compose.yml
└── .env.example
```

---

## 貢献 / チーム開発

- 開発フロー・PR ルール・コミット規約は [`CONTRIBUTING.md`](CONTRIBUTING.md) を必ず読んでください
- 初めての人向けの学習ガイドは [`docs/TUTORIAL.md`](docs/TUTORIAL.md)

---

## ライセンス

MIT
