#!/usr/bin/env bash
# Runs once after the devcontainer is created.
# NOTE: set -e はあえて使わない。1 ステップ失敗してもコンテナ自体は残して手動修復可能に。
set -uo pipefail

echo "==> Installing backend Python dependencies..."
cd /workspace/backend
if ! uv sync 2>&1; then
  echo "   uv sync failed, falling back to pip"
  pip install --user -e ".[dev]" || echo "   pip install も失敗。ターミナルで手動再試行してください。"
fi

echo "==> Installing frontend Node dependencies..."
cd /workspace/frontend
npm install

echo "==> Creating .env from example if missing..."
if [ ! -f /workspace/.env ]; then
  cp /workspace/.env.example /workspace/.env
  echo "   Created /workspace/.env — remember to fill in secrets."
fi

echo "==> Running database migrations..."
cd /workspace/backend
DATABASE_URL=postgresql+psycopg://shifts:shifts_password@db:5432/shifts_db \
  uv run alembic upgrade head || echo "   (migrations skipped: DB may not be ready)"

cat <<'EOF'

╔══════════════════════════════════════════════════════════════╗
║  Devcontainer ready!                                         ║
║                                                              ║
║  ▶ Start backend:                                            ║
║      cd backend && uv run uvicorn app.main:app --reload      ║
║        --host 0.0.0.0 --port 8000                            ║
║                                                              ║
║  ▶ Start frontend:                                           ║
║      cd frontend && npm run dev -- --host 0.0.0.0            ║
║                                                              ║
║  ▶ Or start everything via docker compose (on host):         ║
║      docker compose --profile "" up backend frontend         ║
║                                                              ║
║  ▶ Terraform / gcloud / cloud-sql-proxy also installed.      ║
╚══════════════════════════════════════════════════════════════╝

EOF
