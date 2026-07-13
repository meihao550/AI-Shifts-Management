# Terraform (GCP)

Skeleton for deploying AI-Shifts-Management on Google Cloud Run + Cloud SQL.

## Prereqs

- `gcloud auth application-default login`
- Terraform >= 1.6
- Artifact Registry で backend / frontend の Docker イメージを push 済み

## Push images

```bash
# 例: asia-northeast1 の Artifact Registry
REGION=asia-northeast1
PROJECT=your-project
REPO=ai-shifts

gcloud artifacts repositories create $REPO \
  --repository-format=docker --location=$REGION

docker build -t $REGION-docker.pkg.dev/$PROJECT/$REPO/backend:latest ./backend
docker push $REGION-docker.pkg.dev/$PROJECT/$REPO/backend:latest

docker build -t $REGION-docker.pkg.dev/$PROJECT/$REPO/frontend:latest --target prod ./frontend
docker push $REGION-docker.pkg.dev/$PROJECT/$REPO/frontend:latest
```

## Apply

```bash
cd deploy/terraform
terraform init
terraform apply \
  -var project_id=your-project \
  -var image_backend=asia-northeast1-docker.pkg.dev/your-project/ai-shifts/backend:latest \
  -var image_frontend=asia-northeast1-docker.pkg.dev/your-project/ai-shifts/frontend:latest
```

Cloud Run URL が出力されます。Google OAuth のリダイレクト URI に登録し、
`GOOGLE_REDIRECT_URI` を更新してください。
