#!/usr/bin/env bash
# Runs once after the devcontainer is created.
set -euo pipefail

echo "==> Installing backend Python dependencies..."
cd /workspace/backend
uv sync || pip install --user -e ".[dev]"

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
