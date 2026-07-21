#!/usr/bin/env bash
#
# dev.sh — backend と frontend を 1 コマンドでまとめて起動する開発用スクリプト
#
#   使い方:  ./dev.sh
#   停止:    Ctrl+C （backend / frontend の両方が止まります）
#
# バックエンド: http://localhost:8000  (Swagger: http://localhost:8000/docs)
# フロントエンド: http://localhost:5173
#
set -euo pipefail

# このスクリプトが置かれているディレクトリ（= リポジトリルート）へ移動
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

pids=()

# 終了時に子プロセス（backend / frontend）をまとめて片付ける
cleanup() {
  echo ""
  echo "==> 停止中..."
  for pid in "${pids[@]}"; do
    # プロセスグループごと止める
    kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "==> DB マイグレーションを適用 (alembic upgrade head)"
( cd backend && uv run alembic upgrade head )

echo "==> backend を起動 (http://localhost:8000)"
( cd backend && exec uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 ) &
pids+=($!)

echo "==> frontend を起動 (http://localhost:5173)"
( cd frontend && exec npm run dev -- --host 0.0.0.0 ) &
pids+=($!)

echo "==> 両方起動しました。停止するには Ctrl+C を押してください。"

# どちらかが落ちたらスクリプトも終了する（trap で相方も片付く）
wait -n
