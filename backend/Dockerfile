FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 依存はすべて manylinux wheel で入るため build-essential は不要。
# 本番イメージは dev 依存(pytest/ruff/mypy 等)を含めない（Artifact Registry 容量削減）。
COPY . .
RUN pip install --upgrade pip && pip install -e .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
