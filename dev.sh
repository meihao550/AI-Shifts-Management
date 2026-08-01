#!/usr/bin/env bash
# frontend と backend を同時に起動する開発用スクリプト。
# 使い方: リポジトリのルートで `bash dev.sh`
#        止めるときは Ctrl+C（両方まとめて止まる）
set -uo pipefail

# このスクリプトがある場所（＝リポジトリのルート）へ移動
cd "$(dirname "$0")"

# backend が読む DB 接続先を明示（.env の場所問題を回避し、db サービスを指す）
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://shifts:shifts_password@db:5432/shifts_db}"

# Ctrl+C やスクリプト終了時に、起動した子プロセスをまとめて停止
trap 'kill 0' EXIT

echo "==> backend  → http://localhost:8000"
( cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 ) &

echo "==> frontend → http://localhost:5173"
( cd frontend && npm run dev -- --host 0.0.0.0 ) &

# どちらかが終わるまで待つ（＝Ctrl+C するまで起動しっぱなし）
wait