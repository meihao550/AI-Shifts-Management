# Dev Container

VS Code の Dev Containers 拡張機能で、依存関係が全て入った統一開発環境をワンクリックで起動できます。

## 前提

- VS Code
- [Dev Containers 拡張](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
- Docker Desktop（動作中）

## 使い方

1. VS Code でリポジトリを開く
2. コマンドパレット (`Cmd+Shift+P`) → **Dev Containers: Reopen in Container**
3. 初回はイメージビルドで数分かかります
4. 起動後、コンテナ内のターミナルで作業できます

## 含まれるツール

| ツール | 用途 |
|---|---|
| Python 3.11 + uv | バックエンド |
| Node.js 20 + npm/pnpm | フロントエンド |
| Terraform 1.9.8 | インフラ |
| gcloud CLI + cloud-sql-proxy | GCP デプロイ |
| Docker CLI + Compose | ネスト実行 |
| PostgreSQL client (psql) | DB 操作 |
| Ruff / mypy / ESLint / Prettier | Lint/Format |

## VS Code 拡張機能（自動インストール）

- Vue (Volar)
- Python + Pylance + Ruff
- Terraform + HCL
- ESLint + Prettier
- Docker
- GitLens
- Code Spell Checker

## サービス

Devcontainer と一緒に `db` サービス（PostgreSQL 16）が起動します。`backend` / `frontend` は自動起動しません（profiles=manual）。

### 手動起動

```bash
# コンテナ内で
cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0
cd frontend && npm run dev -- --host 0.0.0.0

# または host の docker compose で全部起動
# （devcontainer 外の macOS ターミナルで）
docker compose up backend frontend db
```

## ポート

自動でフォワードされます：
- 5173 → Vite dev server
- 8000 → FastAPI
- 5432 → PostgreSQL

## トラブルシューティング

### `docker.sock: permission denied`
```bash
sudo chown vscode:docker /var/run/docker.sock
```

### `alembic upgrade head` が失敗
DB がまだ起動中の可能性。少し待ってから再実行：
```bash
DATABASE_URL=postgresql+psycopg://shifts:shifts_password@db:5432/shifts_db \
  uv run alembic upgrade head
```

### イメージを再ビルドしたい
コマンドパレット → **Dev Containers: Rebuild Container**
