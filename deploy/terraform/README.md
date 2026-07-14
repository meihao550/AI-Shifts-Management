# Terraform (GCP)

Cloud Run + Cloud SQL + Secret Manager でのデプロイ用 Terraform です。

**詳細な手順は必ず [`deploy/DEPLOY.md`](../DEPLOY.md) を参照してください。**

## クイックリファレンス

```bash
cd deploy/terraform
terraform init
terraform apply \
  -var project_id=your-project \
  -var region=asia-northeast1 \
  -var image_backend=asia-northeast1-docker.pkg.dev/your-project/ai-shifts/backend:latest \
  -var image_frontend=asia-northeast1-docker.pkg.dev/your-project/ai-shifts/frontend:latest \
  -var allowed_google_domain=""
```

## 前提

- Secret Manager に以下の secret が作成済み（値も投入済み）：
  - `secret-key`
  - `google-client-id`
  - `google-client-secret`
  - `anthropic-api-key`
  - `openai-api-key`
- Artifact Registry に backend / frontend の Docker イメージが push 済み

セットアップ手順の全体像は [`deploy/DEPLOY.md`](../DEPLOY.md) の Step 5〜9 を参照。

## 主要変数

| 変数 | 既定値 | 説明 |
|---|---|---|
| `project_id` | 必須 | GCP プロジェクト ID |
| `region` | `asia-northeast1` | Cloud Run / Cloud SQL のリージョン |
| `image_backend` | 必須 | backend イメージの Artifact Registry URL |
| `image_frontend` | 必須 | frontend イメージの Artifact Registry URL |
| `db_instance_tier` | `db-f1-micro` | Cloud SQL のマシンサイズ |
| `allowed_google_domain` | `""` | ログイン許可する Workspace ドメイン（空なら制限なし） |
| `llm_provider` | `anthropic` | `anthropic` / `openai` / `none` |

## 出力

- `backend_url` — Cloud Run backend の URL
- `frontend_url` — Cloud Run frontend の URL
- `db_public_ip` — Cloud SQL の Public IP
- `db_connection_name` — Cloud SQL Auth Proxy 用の connection name
