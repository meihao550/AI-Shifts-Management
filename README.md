# AI-Shifts-Management

生成AI（LLM）と OR-tools CP-SAT による制約プログラミングを組み合わせた、シフト自動作成・人件費計算 Web アプリケーションです。

## 機能概要

| ID | 機能 | 概要 |
|---|---|---|
| F-1 | AI シフト自動生成 | LLM が自然言語の追加事情（イベント、有休など）を JSON 制約に変換し、CP-SAT が全体最適化してシフトを出力 |
| F-2 | 人件費自動計算 | 深夜割増を含む人件費計算、月間労働時間に応じた社会保険/雇用保険の適用判定 |
| F-3 | 従業員管理 | 名前・年齢・交通費・メインシフト・週勤務回数などの詳細管理 |
| F-4 | ルール設定 | 曜日別必要人員数、シフトパターン、割増率などの設定 |
| F-5 | PDF/Excel 出力 | 印刷プレビュー画面から PDF・Excel でシフト表を出力 |
| F-6 | 認証 | Google Workspace OAuth（社員/管理者ロール） |

## 技術スタック

| レイヤ | 技術 |
|---|---|
| Frontend | Vue 3 + TypeScript + Vite + Vue Router + Pinia + Naive UI |
| Backend  | FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic |
| Optimize | OR-tools CP-SAT |
| LLM      | Anthropic Claude または OpenAI（`.env` で切替） |
| DB       | PostgreSQL 16 |
| 認証     | Google OAuth 2.0 + JWT |
| 開発     | Docker Compose / uv / npm / Ruff / mypy / ESLint / Prettier / Vitest / Pytest |
| デプロイ | GCP (Cloud Run + Cloud SQL) + Terraform 雛形 |

## クイックスタート（Docker Compose）

```bash
# 1. リポジトリ直下で .env を作成
cp .env.example .env

# 2. .env の以下を設定
# - GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / ALLOWED_GOOGLE_DOMAIN
# - ANTHROPIC_API_KEY もしくは OPENAI_API_KEY
# - SECRET_KEY （openssl rand -hex 32 で生成）

# 3. 起動
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend (Swagger UI): http://localhost:8000/docs
- PostgreSQL: localhost:5432

初回起動時に Alembic が自動的に `alembic upgrade head` を実行し、シードデータ用エンドポイント `POST /api/dev/seed` から開発用データを投入できます（`ENVIRONMENT=development` のときのみ有効）。

## 手動起動（Docker を使わない場合）

### バックエンド

```bash
cd backend
uv sync            # pyproject.toml から依存を解決
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

### フロントエンド

```bash
cd frontend
npm install
npm run dev
```

## ユーザーが自分で行う必要のある設定

以下は本アプリを本番運用するために **人手が必要な設定** です。

1. **Google Cloud Console**
   - OAuth 2.0 クライアント ID の発行 (`Web application`)
   - リダイレクト URI に `http://localhost:8000/api/auth/google/callback`（開発）と本番 URL を登録
   - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` を `.env` に設定
   - Google Workspace ドメインで制限したい場合は `ALLOWED_GOOGLE_DOMAIN=example.co.jp`
2. **LLM API キー**
   - Anthropic を使う場合: https://console.anthropic.com/ で API キー発行 → `ANTHROPIC_API_KEY`
   - OpenAI を使う場合: https://platform.openai.com/ で API キー発行 → `OPENAI_API_KEY`
   - `LLM_PROVIDER=anthropic` または `openai` を選択
3. **SECRET_KEY** の生成
   ```bash
   openssl rand -hex 32
   ```
   を `.env` の `SECRET_KEY` に設定。
4. **初期管理者ユーザー**
   - 初回起動後、DB に登録される 1 人目のユーザーは自動的に `admin` ロールになります（`app/routers/auth.py` 参照）。
   - 追加ユーザーは 初期状態は `employee`。管理者が管理画面（従業員管理）から昇格可能。
5. **本番環境変数**
   - `ENVIRONMENT=production` に変更
   - `FRONTEND_ORIGIN` と `GOOGLE_REDIRECT_URI` を本番の HTTPS URL に更新
   - PostgreSQL は Cloud SQL 等マネージド DB を推奨
6. **人件費計算ロジック確認**
   - 深夜割増率・割増賃金は法定 25% 以上（22:00–翌 5:00）で計算。
   - 有給・交通費の月次組み込み方法は運用ポリシーが未確定のため、`backend/app/services/payroll.py` の TODO コメントに沿って先方に確認の上、必要に応じて修正してください。

## テスト

```bash
# backend
cd backend && uv run pytest

# frontend
cd frontend && npm run test:unit
```

## ディレクトリ構成

```
AI-Shifts-Management/
├── backend/          FastAPI + CP-SAT
│   ├── app/
│   │   ├── auth/     Google OAuth + JWT
│   │   ├── core/     設定・DB接続
│   │   ├── models/   SQLAlchemy モデル
│   │   ├── schemas/  Pydantic スキーマ
│   │   ├── routers/  API エンドポイント
│   │   └── services/ CP-SAT / LLM / 人件費
│   ├── alembic/      マイグレーション
│   └── tests/
├── frontend/         Vue3 + Naive UI
│   └── src/
│       ├── api/      APIクライアント
│       ├── router/   Vue Router
│       ├── stores/   Pinia
│       ├── views/    画面
│       └── components/
├── deploy/
│   └── terraform/    GCP 用 Terraform 雛形
├── docker-compose.yml
├── .env.example
└── docs/Project.pdf  企画書
```

## ライセンス


# AI-Shifts-Management
