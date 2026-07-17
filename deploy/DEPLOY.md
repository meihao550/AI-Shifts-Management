# デプロイ手順（GCP Cloud Run + Supabase Postgres）

このドキュメントに沿って作業すれば、**ローカル環境から本番運用まで到達**できます。

- 構成：**Supabase** に Postgres、**Cloud Run** に backend / frontend を配置
- 所要時間の目安：初回 60〜90 分（GCP アカウント作成含まず）
- 月額コスト：**基本 ¥0**（Supabase 無料枠 + Cloud Run 無料枠 で完結）。予算アラート ¥100/月 も自動セット
- 従来案の Cloud SQL（月 ¥1,300〜） は不要になりました

## なぜ Supabase？

| 項目 | Cloud SQL (旧案) | Supabase (現案) |
|---|---|---|
| 費用 | 月 ¥1,300〜 | **0 円（無料枠）** |
| クレカ | 必須 | 不要 |
| ストレージ | 10 GB〜 | 500 MB |
| 転送 | 従量課金 | 2 GB/月 |
| 自動停止 | なし | 7 日アクセスなしで停止（次アクセスで自動復帰） |

シフト管理システムは 25 名 × 数か月分の割当データで **数 MB** しか使わないので、Supabase 無料枠で十分です。

---

## 目次

1. [事前準備](#1-事前準備)
2. [GCP プロジェクトの作成](#2-gcp-プロジェクトの作成)
3. [gcloud CLI のセットアップ](#3-gcloud-cli-のセットアップ)
4. [Supabase で Postgres を作成](#4-supabase-で-postgres-を作成)
5. [必要な API を有効化](#5-必要な-api-を有効化)
6. [Google OAuth クライアント ID の発行](#6-google-oauth-クライアント-id-の発行)
7. [LLM API キーの取得](#7-llm-api-キーの取得)
8. [Artifact Registry の作成 & イメージ push](#8-artifact-registry-の作成--イメージ-push)
9. [Secret Manager に機密値を登録](#9-secret-manager-に機密値を登録)
10. [Terraform でインフラ構築](#10-terraform-でインフラ構築)
11. [DB マイグレーション実行](#11-db-マイグレーション実行)
12. [OAuth リダイレクト URI と FRONTEND_ORIGIN を更新](#12-oauth-リダイレクト-uri-と-frontend_origin-を更新)
13. [初回ログイン](#13-初回ログイン)
14. [予算アラートの確認](#14-予算アラートの確認)
15. [独自ドメイン & HTTPS（オプション）](#15-独自ドメイン--httpsオプション)
16. [更新・再デプロイ](#16-更新再デプロイ)
17. [破棄・撤収（teardown）](#17-破棄撤収teardown)
18. [トラブルシューティング](#18-トラブルシューティング)
19. [代替：完全に無料の別構成](#19-代替完全に無料の別構成)

---

## 1. 事前準備

以下がインストールされていることを確認してください。

| ツール | バージョン | 確認コマンド |
|---|---|---|
| gcloud CLI | 最新 | `gcloud --version` |
| Terraform | ≥ 1.6 | `terraform version` |
| Docker | Desktop | `docker --version` |
| Git | 任意 | `git --version` |

インストール：
```bash
# macOS (Homebrew)
brew install --cask google-cloud-sdk
brew install terraform
brew install --cask docker
```

また、以下の**アカウント**が必要です。

- Google Cloud アカウント（新規なら $300 のクレジットあり）
- Google Cloud Console にログイン可能な Google アカウント
- Anthropic **または** OpenAI アカウント（LLM 機能を使う場合）

---

## 2. GCP プロジェクトの作成

```bash
# プロジェクト ID を決める（世界で一意）
export PROJECT_ID=ai-shifts-yourname-001
export REGION=asia-northeast1   # 東京。大阪なら asia-northeast2

# プロジェクト作成
gcloud projects create $PROJECT_ID --name="AI Shifts Management"

# 課金アカウントの紐付け（下の ID は自分の Billing Account ID に置き換え）
gcloud billing accounts list
gcloud billing projects link $PROJECT_ID --billing-account=XXXXXX-XXXXXX-XXXXXX
```

> 課金アカウント未設定だと Cloud SQL / Cloud Run が使えません。

---

## 3. gcloud CLI のセットアップ

```bash
gcloud auth login                                # ブラウザで Google ログイン
gcloud auth application-default login            # Terraform 用の ADC
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION
```

---

## 4. Supabase で Postgres を作成

**クレカ不要・完全無料**。

1. https://supabase.com/dashboard にアクセスして GitHub / Google でサインアップ
2. **New project** をクリック
   - Name: `ai-shifts`
   - Database Password: 強力なパスワードを設定（**必ずメモ**）
   - Region: `Northeast Asia (Tokyo)`
   - Plan: **Free**
3. プロジェクト作成に 2〜3 分
4. **Project Settings → Database → Connection string → URI** から接続文字列をコピー
   ```
   postgresql://postgres.xxxxxxxxxxxx:[YOUR-PASSWORD]@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres
   ```
5. `[YOUR-PASSWORD]` を Step 2 のパスワードに置換
6. **SQLAlchemy 用にスキーマドライバを追加**：先頭を `postgresql+psycopg://` に変更
   ```
   postgresql+psycopg://postgres.xxxxxxxxxxxx:実際のPW@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres
   ```
7. この URL は Step 9 で Secret Manager (`database-url`) に登録します

> `pooler` 経由の接続は無料枠でも同時接続が安定します。直接接続用 URL（`db.xxxx.supabase.co:5432`）は避けてください。

---

## 5. 必要な API を有効化

Terraform 内でも `google_project_service` で有効化していますが、`terraform apply` 前に必須のものだけは先に手動で有効化しておくとスムーズです。

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  iam.googleapis.com
```

---

## 6. Google OAuth クライアント ID の発行

1. [Google Cloud Console → APIs & Services → OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent)
   - User Type: **Internal**（Workspace ドメイン内で使う場合）または **External**
   - アプリ名、サポートメール、開発者連絡先を入力し、保存
2. [Credentials → Create Credentials → OAuth client ID](https://console.cloud.google.com/apis/credentials)
   - Application type: **Web application**
   - Name: `AI-Shifts-Management`
   - **Authorized redirect URIs**: いったん `http://localhost:8000/api/auth/google/callback` を入れて作成（本番 URL は Cloud Run デプロイ後に追加）
3. **Client ID / Client secret** を保存（後で Secret Manager に登録）

> 特定の Google Workspace ドメインからしかログインさせたくない場合、Terraform 変数 `allowed_google_domain` にドメインを指定（例：`example.co.jp`）。

---

## 7. LLM API キーの取得

Anthropic を使う場合:
- https://console.anthropic.com/ で API キー発行
- Terraform 変数 `llm_provider` は既定の `anthropic` のまま

OpenAI を使う場合:
- https://platform.openai.com/api-keys で API キー発行
- Terraform 変数 `llm_provider` を `openai` に変更

**両方を Secret Manager に空値でも登録可能**（使わない方は空文字を入れる）。

---

## 8. Artifact Registry の作成 & イメージ push

Docker イメージを GCP 上に配置します。

```bash
# 1. リポジトリ作成
gcloud artifacts repositories create ai-shifts \
  --repository-format=docker \
  --location=$REGION \
  --description="AI-Shifts container images"

# 2. Docker が Artifact Registry にログインできるよう設定
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# 3. リポジトリ直下から backend / frontend をビルド & push
REPO=${REGION}-docker.pkg.dev/${PROJECT_ID}/ai-shifts

# --- backend ---
docker build --platform=linux/amd64 -t $REPO/backend:latest ./backend
docker push $REPO/backend:latest

# --- frontend（本番用 nginx ステージ）---
docker build --platform=linux/amd64 --target prod -t $REPO/frontend:latest ./frontend
docker push $REPO/frontend:latest
```

> Apple Silicon (M1/M2/M3) から push する場合は `--platform=linux/amd64` が必須。付け忘れると Cloud Run で起動失敗します。

イメージが登録されたか確認：
```bash
gcloud artifacts docker images list $REPO --include-tags
```

---

## 9. Secret Manager に機密値を登録

Terraform で Secret 本体（＝空の箱）は作りますが、**値の投入はセキュリティ上手動で行います**。

**先に手動で Secret を作って登録**するのがトラブル少なめです。

```bash
# 1. Secret を作成
for s in secret-key google-client-id google-client-secret anthropic-api-key openai-api-key database-url; do
  gcloud secrets create $s --replication-policy=automatic 2>/dev/null || true
done

# 2. 値を投入

# SECRET_KEY (JWT 署名用)
openssl rand -hex 32 | gcloud secrets versions add secret-key --data-file=-

# Supabase Postgres 接続 URL（Step 4 でコピーしたもの、psycopg スキーマ付き）
echo -n "postgresql+psycopg://postgres.xxxx:PASSWORD@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres" \
  | gcloud secrets versions add database-url --data-file=-

# Google OAuth
echo -n "YOUR_GOOGLE_CLIENT_ID"     | gcloud secrets versions add google-client-id --data-file=-
echo -n "YOUR_GOOGLE_CLIENT_SECRET" | gcloud secrets versions add google-client-secret --data-file=-

# Anthropic / OpenAI（使わない方は空文字を入れておく）
echo -n "sk-ant-YOUR_KEY" | gcloud secrets versions add anthropic-api-key --data-file=-
echo -n ""                | gcloud secrets versions add openai-api-key    --data-file=-
```

---

## 10. Terraform でインフラ構築

```bash
cd deploy/terraform

# 初期化
terraform init
```

### 変数の渡し方（どちらか）

#### 方法 A: `terraform.tfvars` を使う（推奨）

```bash
cp terraform.tfvars.example terraform.tfvars
# エディタで開いて project_id / image_backend / image_frontend などを書き換え
```

その後：

```bash
terraform plan
terraform apply
```

#### 方法 B: `-var` フラグで渡す

**注意**: `$PROJECT_ID` などの環境変数は `export` した同じシェルセッションでしか使えません。別ターミナルで動かす場合は再 export、もしくは方法 A を使ってください。

```bash
export PROJECT_ID=your-project-id
export REGION=asia-northeast1

terraform apply \
  -var project_id=$PROJECT_ID \
  -var region=$REGION \
  -var image_backend=${REGION}-docker.pkg.dev/${PROJECT_ID}/ai-shifts/backend:latest \
  -var image_frontend=${REGION}-docker.pkg.dev/${PROJECT_ID}/ai-shifts/frontend:latest \
  -var allowed_google_domain=""
```

**よくあるエラー**:
```
Error: expected a non-empty string
  provider "google" { project = "" }
```
→ `$PROJECT_ID` が空です。`echo $PROJECT_ID` で確認 → 空なら再 export、または `terraform.tfvars` に切り替え。

完了時に URL が出力されます：

```
Outputs:
backend_url  = "https://ai-shifts-backend-XXXX.a.run.app"
frontend_url = "https://ai-shifts-frontend-XXXX.a.run.app"
db_public_ip = "35.xxx.xxx.xxx"
db_connection_name = "your-project:asia-northeast1:ai-shifts-db"
```

これらを控えておいてください（次以降のステップで使います）。

---

## 11. DB マイグレーション実行

Supabase Postgres に Alembic のマイグレーションを適用します。**Supabase は Public インターネットから直接接続可能**なので、ローカルからそのまま流せます。

```bash
cd backend

# Step 4 で作った URL をそのまま渡すだけ
DATABASE_URL="postgresql+psycopg://postgres.xxxx:PASSWORD@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres" \
  uv run alembic upgrade head
```

出力に `Running upgrade -> 0001` と表示されれば成功。

Supabase Dashboard → **Database → Tables** で `employees`, `shifts`, `shift_patterns` などが作られているのを確認できます。

> `uv` を使わない場合は `python -m alembic upgrade head` でも OK。事前に `pip install -e ".[dev]"` が必要。

---

## 12. OAuth リダイレクト URI と FRONTEND_ORIGIN を更新

Cloud Run の URL が確定したので、以下 2 箇所を更新します。

### (a) Google OAuth の Authorized redirect URIs に追加

[Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials) → OAuth client → Authorized redirect URIs に以下を追加：

```
<backend_url>/api/auth/google/callback
```

例：
```
https://ai-shifts-backend-XXXX.a.run.app/api/auth/google/callback
```

Authorized JavaScript origins にも frontend URL を追加：
```
https://ai-shifts-frontend-XXXX.a.run.app
```

### (b) Cloud Run backend の env vars を更新

`FRONTEND_ORIGIN` と `GOOGLE_REDIRECT_URI` を実 URL に置き換えます。

```bash
BACKEND_URL=$(terraform output -raw backend_url)
FRONTEND_URL=$(terraform output -raw frontend_url)

gcloud run services update ai-shifts-backend \
  --region=$REGION \
  --update-env-vars="FRONTEND_ORIGIN=${FRONTEND_URL},GOOGLE_REDIRECT_URI=${BACKEND_URL}/api/auth/google/callback"
```

### (c) frontend の VITE_API_BASE_URL を再ビルド

フロントエンドはビルド時に環境変数が焼き込まれるため、backend URL が確定したら再ビルド & push が必要です。

```bash
# .env.production を作って backend URL を指定
cat > frontend/.env.production <<EOF
VITE_API_BASE_URL=${BACKEND_URL}
EOF

# 再ビルド & push
docker build --platform=linux/amd64 --target prod \
  -t $REPO/frontend:latest ./frontend
docker push $REPO/frontend:latest

# Cloud Run を新しいイメージにローリング更新
gcloud run services update ai-shifts-frontend \
  --region=$REGION \
  --image=$REPO/frontend:latest
```

---

## 13. 初回ログイン

1. ブラウザで `<frontend_url>` を開く
2. 「Google Workspace でログイン」ボタンで OAuth ログイン
3. **最初にログインした Google アカウントが自動的に admin ロール** になります（`backend/app/routers/auth.py` で判定）
4. 初回はデータが空なので、以下いずれかで初期データを入れます

### 方法 A: 従業員管理画面から手動入力
- ヘッダの「従業員管理」→ 「+ 新規従業員」で 25 名程度追加
- ヘッダの「ルール設定」→ シフトパターン・必要人員を確認

### 方法 B: dev/seed エンドポイントを呼ぶ（**本番では無効**）
本番では `ENVIRONMENT=production` のため dev エンドポイントは 404 を返します。**開発モードで検証したい場合のみ**、Cloud Run の env var を一時的に development に切り替えて実行してください。

---

## 14. 予算アラートの確認

`terraform.tfvars` で `budget_notification_email` を指定していれば、Terraform が自動で以下をセットアップします：

- 月次予算: `budget_amount_jpy`（既定 ¥100）
- 通知閾値: 50% / 90% / 100% で指定メールに通知
- 通知チャンネル: Cloud Monitoring 経由

まだ設定していなければ：

```bash
# tfvars に追記
budget_notification_email = "you@example.com"

# 反映
cd deploy/terraform
terraform apply
```

**注意**: 予算アラートは**通知するだけ**で、閾値超過時にリソースが自動停止する機能ではありません。完全に課金を防ぎたい場合は、通知を受け取った時点で手動でサービスを停止するか、以下も併用してください：

```bash
# Cloud Run を一時停止（インスタンス数を 0 に固定）
gcloud run services update ai-shifts-backend --region=$REGION --max-instances=0
gcloud run services update ai-shifts-frontend --region=$REGION --max-instances=0
```

Supabase 側は無料枠を超えるとアクセスが拒否されるだけで、勝手に課金されることはありません（クレカ登録していない限り）。

---

## 15. 独自ドメイン & HTTPS（オプション）

Cloud Run はデフォルトで `.run.app` サブドメインを持ちますが、独自ドメインを紐付けたい場合：

```bash
# 1. ドメインの所有権を確認
gcloud domains verify shifts.example.com

# 2. Cloud Run にマッピング
gcloud beta run domain-mappings create \
  --service=ai-shifts-frontend \
  --domain=shifts.example.com \
  --region=$REGION

# 3. 表示された DNS レコード（CNAME/A）を DNS プロバイダに登録
# 4. HTTPS 証明書は Google が自動で発行（数分〜数十分）
```

backend にも `api.shifts.example.com` などを紐付ける想定なら、同じ手順で `ai-shifts-backend` にマッピングします。その後、Google OAuth の redirect URI・Cloud Run の env vars・frontend の `VITE_API_BASE_URL` を独自ドメインに更新して再ビルドしてください。

---

## 16. 更新・再デプロイ

コードを更新したら、対象サービスを再ビルド & push → Cloud Run に反映します。

### backend の更新
```bash
docker build --platform=linux/amd64 -t $REPO/backend:latest ./backend
docker push $REPO/backend:latest
gcloud run services update ai-shifts-backend --region=$REGION --image=$REPO/backend:latest
```

### frontend の更新
```bash
docker build --platform=linux/amd64 --target prod -t $REPO/frontend:latest ./frontend
docker push $REPO/frontend:latest
gcloud run services update ai-shifts-frontend --region=$REGION --image=$REPO/frontend:latest
```

### DB マイグレーション追加時
- `backend/alembic/versions/` に新しいマイグレーションを追加
- Supabase URL を渡して `alembic upgrade head` を実行（[Step 11](#11-db-マイグレーション実行)と同じ手順）

### タグを打って本番と staging を分ける（推奨）
```bash
docker tag $REPO/backend:latest $REPO/backend:$(git rev-parse --short HEAD)
docker push $REPO/backend:$(git rev-parse --short HEAD)
```
`gcloud run services update` で特定タグを指定すれば、ロールバックも `--image=$REPO/backend:<前のSHA>` で可能。

---

## 17. 破棄・撤収（teardown）

```bash
cd deploy/terraform
terraform destroy

# 手動作成したものも削除
gcloud secrets list
gcloud artifacts repositories delete ai-shifts --location=$REGION

# Supabase 側はダッシュボードから Settings → General → Delete project
```

**プロジェクトごと消すのが最も確実**：
```bash
gcloud projects delete $PROJECT_ID
```
（30 日間は復元可能）

---

## 18. トラブルシューティング

### `terraform apply` で Cloud Run 起動時に "container failed to start"
- **原因**: Docker イメージのアーキテクチャ不一致（Apple Silicon で `--platform=linux/amd64` 忘れ）
- **対処**: [Step 7](#7-artifact-registry-の作成--イメージ-push) に沿って再ビルド

### ログインしたが 500 エラー / DB 接続失敗
- Cloud Run のログを確認：
  ```bash
  gcloud run services logs read ai-shifts-backend --region=$REGION --limit=50
  ```
- Cloud SQL の `authorized_networks` を Cloud Run の egress IP に絞る場合は、Cloud SQL Auth Proxy sidecar か Private Service Connect を使うのが本命です

### Google OAuth で `redirect_uri_mismatch`
- OAuth Client の Authorized redirect URIs に `<backend_url>/api/auth/google/callback` を **完全一致** で登録しているか
- 末尾スラッシュ有無、http/https、大文字小文字に注意

### `email-validator is not installed`
- backend の `pyproject.toml` は `pydantic[email]` を含むはずですが、古いイメージを使っている可能性があるため再ビルドしてください

### CP-SAT が INFEASIBLE
- 有効な従業員数 < 1 日必要人員合計 の場合は 400 エラーで案内が出ます
- 有効人数を増やすか、ルール設定で必要人員を減らしてください

### `Secret Manager permission denied`
- Cloud Run のランタイム SA（デフォルトでは `<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`）に `roles/secretmanager.secretAccessor` が付与されているか確認
- Terraform で自動付与されるはずですが、失敗した場合は手動で追加可能：
  ```bash
  gcloud secrets add-iam-policy-binding secret-key \
    --member="serviceAccount:$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')-compute@developer.gserviceaccount.com" \
    --role=roles/secretmanager.secretAccessor
  ```

---

## 19. 代替：完全に無料の別構成

GCP を全く使わず、クレカ不要で完結させたい場合：

| 選択肢 | 費用 | クレカ | 特徴 |
|---|---|---|---|
| **Supabase + 自宅 Docker + Cloudflare Tunnel** | ¥0 | 不要 | Mac を閉じると停止 |
| **Supabase + Render web** | ¥0 (15分でスリープ) | 不要 | 冷起動 30 秒 |
| **Supabase + Fly.io** | ¥0 | 必要 | 3 VM 無料枠 |

### 自宅 Docker + Cloudflare Tunnel 手順（一番安全）

```bash
# 1. .env に Supabase URL を設定
DATABASE_URL=postgresql+psycopg://postgres.xxxx:PASSWORD@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres

# 2. Docker Compose 起動
docker compose up backend frontend

# 3. Cloudflare Tunnel（無料、要 Cloudflare アカウント）
brew install cloudflared
cloudflared tunnel --url http://localhost:5173
# → https://random-name.trycloudflare.com が発行される
```

Cloudflare アカウントに正規で登録すれば独自サブドメイン（例: shifts.yourdomain.com）にも紐付け可能で、Mac がスリープすると止まりますが、**外部への課金リスクゼロ**です。

---

## 補足：CI/CD 化

`.github/workflows/ci.yml` は既にテスト・ビルドが動く状態です。デプロイまで自動化するには、GitHub Actions に以下を追加します。

```yaml
# .github/workflows/deploy.yml（雛形）
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL/providers/PROVIDER
          service_account: cd-deployer@PROJECT_ID.iam.gserviceaccount.com
      - uses: google-github-actions/setup-gcloud@v2
      - run: gcloud auth configure-docker asia-northeast1-docker.pkg.dev
      - name: Build & push backend
        run: |
          docker build --platform=linux/amd64 -t asia-northeast1-docker.pkg.dev/${{ vars.PROJECT_ID }}/ai-shifts/backend:${{ github.sha }} ./backend
          docker push asia-northeast1-docker.pkg.dev/${{ vars.PROJECT_ID }}/ai-shifts/backend:${{ github.sha }}
      - name: Deploy backend
        run: gcloud run services update ai-shifts-backend --region=asia-northeast1 --image=asia-northeast1-docker.pkg.dev/${{ vars.PROJECT_ID }}/ai-shifts/backend:${{ github.sha }}
```

Workload Identity Federation を設定すれば、サービスアカウントキー JSON を GitHub に置かずに済みます（推奨）。設定手順は [公式ガイド](https://cloud.google.com/iam/docs/workload-identity-federation) 参照。
