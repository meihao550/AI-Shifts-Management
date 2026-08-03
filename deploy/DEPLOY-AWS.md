# デプロイ手順（AWS App Runner + S3/CloudFront + Supabase Postgres）

このドキュメントは **AWS を学びながら**（学校の授業・試験対策を兼ねて）、このアプリを AWS 上で本番運用するための手順書です。
各ステップに **📚学習メモ**（試験で問われやすいポイント）を付けています。まず概念を理解し、そのまま手を動かして定着させる構成です。

- 構成：**Supabase** に Postgres（継続利用）、**App Runner** に backend、**S3 + CloudFront** に frontend
- DB を Supabase のままにするので、**VPC / Subnet / Security Group を自分で設計する必要がありません**（＝最初のハードルが低い）
- 所要時間の目安：初回 60〜90 分
- 月額コスト目安（東京リージョン `ap-northeast-1`）：
  - S3 + CloudFront … この規模ならほぼ **¥0〜数十円**
  - App Runner … 最小構成で **月 $5〜10 程度**（起動しっぱなしの場合。使わない時は一時停止で節約可）
  - Supabase … 無料枠 **¥0**
  - ⚠️ App Runner は「scale-to-zero（完全ゼロ課金）」が無いため、GCP Cloud Run より最低費用がかかります。学習が終わったら **必ず撤収（第11章）** しましょう。

---

## 📚 まずこれだけ：AWS と GCP の思想の違い

| 観点 | GCP（今まで） | AWS（これから） |
|---|---|---|
| ネットワーク | 自動でよしなに | **自分で VPC を組む前提**（※今回は Supabase 継続で回避） |
| 権限 | IAM（ロール中心） | **IAM（ユーザー / ロール / ポリシー）** ← 事故の大半はここ |
| コンテナ実行 | Cloud Run | **App Runner**（Cloud Run に一番近い） |
| 機密管理 | Secret Manager | **SSM Parameter Store**（標準は無料）/ Secrets Manager |
| イメージ置き場 | Artifact Registry | **ECR** |
| 監視・予算 | Cloud Monitoring / Budget | **CloudWatch / AWS Budgets** |
| CLI | `gcloud` | `aws` |

---

## サービス対応図

```
   ユーザー
     │
     ├──[ https ]──►  CloudFront ──►  S3 (静的サイト)      … フロント(Vue ビルド成果物)
     │
     └──[ /api ]───►  App Runner ──►  Supabase (Postgres) … backend(FastAPI コンテナ)
                          │
                          ├─ ECR                 … Docker イメージ
                          └─ SSM Parameter Store  … SECRET_KEY / DATABASE_URL / API キー
```

---

## 目次

1. [事前準備（ツール）](#1-事前準備ツール)
2. [AWS アカウント初期設定（IAM・MFA・予算アラート）](#2-aws-アカウント初期設定iammfa予算アラート)
3. [AWS CLI のセットアップ](#3-aws-cli-のセットアップ)
4. [ECR を作成して backend イメージを push](#4-ecr-を作成して-backend-イメージを-push)
5. [SSM Parameter Store に機密値を登録](#5-ssm-parameter-store-に機密値を登録)
6. [App Runner に backend をデプロイ](#6-app-runner-に-backend-をデプロイ)
7. [DB マイグレーション実行（Supabase）](#7-db-マイグレーション実行supabase)
8. [フロントを S3 + CloudFront で配信](#8-フロントを-s3--cloudfront-で配信)
9. [OAuth リダイレクト URI と FRONTEND_ORIGIN を更新](#9-oauth-リダイレクト-uri-と-frontend_origin-を更新)
10. [初回ログインと動作確認](#10-初回ログインと動作確認)
11. [更新・再デプロイ](#11-更新再デプロイ)
12. [撤収（teardown）](#12-撤収teardown)
13. [トラブルシューティング](#13-トラブルシューティング)
14. [用語集（試験対策）](#14-用語集試験対策)

---

## 1. 事前準備（ツール）

| ツール | 確認コマンド |
|---|---|
| AWS CLI v2 | `aws --version` |
| Docker Desktop | `docker --version` |
| uv（or Python） | `uv --version` |
| Node.js 20 | `node --version` |
| Git | `git --version` |

AWS CLI が無ければ [公式手順](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) でインストールしてください（Mac は `brew install awscli`）。

---

## 2. AWS アカウント初期設定（IAM・MFA・予算アラート）

> 📚**学習メモ：IAM（Identity and Access Management）**
> AWS で最重要のサービス。「誰が(ユーザー/ロール)」「何を(ポリシー)」できるかを制御します。
> - **ルートユーザー**＝アカウント作成時のメールアドレスのアカウント。**最強の権限**なので普段使い禁止。
> - **IAM ユーザー**＝日常操作用。最小権限を付与する。
> - **IAM ロール**＝人ではなくサービス（App Runner 等）に権限を渡す仕組み。パスワードを持たない。
> - **MFA（多要素認証）**＝ルートには必ず設定。試験でも「ルートに MFA」は頻出。

作業：

1. AWS マネジメントコンソールにルートでログイン
2. **ルートユーザーに MFA を設定**（スマホの認証アプリ等）
3. IAM で**自分用の管理者 IAM ユーザー**を作成（`AdministratorAccess` ポリシー）＋ MFA 設定
   - 以後の作業はこの IAM ユーザーで行う（ルートはログアウト）
4. **予算アラートを設定**（課金事故防止・最優先）

> 📚**学習メモ：AWS Budgets**
> 「月 ¥X を超えそうならメール通知」を設定する。GCP の Budget と同じ発想。無料枠を超えた瞬間に気づけるので、学習用アカウントでは**最初に必ず設定**。

- コンソール → **Billing and Cost Management → Budgets → Create budget**
- Template: **Monthly cost budget**、金額 例 **$10**、通知先に自分のメール
- 50% / 80% / 100% の3段階でアラートが飛ぶように設定

---

## 3. AWS CLI のセットアップ

第2章で作った IAM ユーザーで **アクセスキー**を発行し、CLI に設定します。

> 📚**学習メモ：アクセスキー**
> CLI/プログラムから AWS を操作するための鍵（Access Key ID + Secret Access Key）。**流出＝不正利用**に直結するので Git に絶対コミットしない。将来的には GitHub Actions では鍵を持たない **OIDC 連携**が推奨（本書末尾で触れます）。

```bash
aws configure
# AWS Access Key ID     : （発行したキー）
# AWS Secret Access Key : （発行したシークレット）
# Default region name   : ap-northeast-1
# Default output format : json
```

確認：

```bash
aws sts get-caller-identity
```

自分の IAM ユーザーの ARN とアカウント ID が表示されれば OK。以降、`<ACCOUNT_ID>` はここで出た12桁の数字に読み替えてください。

---

## 4. ECR を作成して backend イメージを push

> 📚**学習メモ：ECR（Elastic Container Registry）**
> Docker イメージを保管する AWS のプライベートレジストリ。GCP の Artifact Registry に相当。App Runner はここからイメージを取得して動かす。

### 4-1. リポジトリ作成

```bash
aws ecr create-repository --repository-name ai-shifts-backend --region ap-northeast-1
```

### 4-2. Docker を ECR にログインさせる

```bash
aws ecr get-login-password --region ap-northeast-1 \
  | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.ap-northeast-1.amazonaws.com
```

### 4-3. ビルドして push

> ⚠️ App Runner は **linux/amd64** で動きます。Apple Silicon（M1/M2/M3）でビルドする場合は `--platform linux/amd64` を必ず付けてください（付けないと「exec format error」で起動失敗）。

```bash
cd backend

docker build --platform linux/amd64 -t ai-shifts-backend .

docker tag ai-shifts-backend:latest \
  <ACCOUNT_ID>.dkr.ecr.ap-northeast-1.amazonaws.com/ai-shifts-backend:latest

docker push \
  <ACCOUNT_ID>.dkr.ecr.ap-northeast-1.amazonaws.com/ai-shifts-backend:latest
```

---

## 5. SSM Parameter Store に機密値を登録

> 📚**学習メモ：SSM Parameter Store**
> 設定値・機密値を安全に保管するサービス。`SecureString` 型は **KMS** で暗号化される。**標準パラメータは無料**（Secrets Manager は1シークレットあたり月 $0.40 かかるので、学習用途では Parameter Store が有利）。
> App Runner は起動時にこれらを読み込んで、コンテナの環境変数に注入できる。

登録するもの（backend の `app/core/config.py` が読む環境変数に対応）：

```bash
REGION=ap-northeast-1

# アプリ秘密鍵（ランダム生成）
aws ssm put-parameter --region $REGION --type SecureString \
  --name /ai-shifts/SECRET_KEY --value "$(openssl rand -hex 32)"

# Supabase の接続 URL（第4章 DEPLOY.md で使ったものと同じ。driver は postgresql+psycopg）
aws ssm put-parameter --region $REGION --type SecureString \
  --name /ai-shifts/DATABASE_URL \
  --value "postgresql+psycopg://postgres.xxxx:PASSWORD@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

# Google OAuth
aws ssm put-parameter --region $REGION --type SecureString \
  --name /ai-shifts/GOOGLE_CLIENT_ID --value "xxxx.apps.googleusercontent.com"
aws ssm put-parameter --region $REGION --type SecureString \
  --name /ai-shifts/GOOGLE_CLIENT_SECRET --value "xxxx"

# LLM（使う方だけでOK）
aws ssm put-parameter --region $REGION --type SecureString \
  --name /ai-shifts/ANTHROPIC_API_KEY --value "sk-ant-xxxx"
```

> 💡 Supabase の接続 URL は Supabase Dashboard → **Project Settings → Database → Connection string** から取得できます。**Connection pooler（ポート 6543）** の URI を使うのが推奨（App Runner は接続が増減するため）。

---

## 6. App Runner に backend をデプロイ

> 📚**学習メモ：AWS App Runner**
> コンテナを渡すだけで HTTPS 付き URL・オートスケール・ロードバランシングを**フルマネージド**で提供するサービス。GCP Cloud Run に最も近い。
> - **ECS Fargate** … より細かく制御できるが、ALB・VPC・タスク定義など自分で組む必要があり学習コスト高。
> - **Lambda** … 完全サーバーレス・ゼロ課金にできるが、常駐処理や大きな依存（OR-Tools 等）には工夫が要る。
> - このアプリ規模なら **App Runner が最適**。
>
> App Runner では **2種類の IAM ロール**を使う（試験でも「サービスにロールで権限を渡す」は頻出）：
> 1. **Access role** … App Runner が **ECR からイメージを取得**するための権限（`AWSAppRunnerServicePolicyForECRAccess`）
> 2. **Instance role** … **動いているコンテナ自身**が Parameter Store を読むための権限

### 6-1. Instance role を作成（コンテナが Parameter Store を読むため）

コンソール → **IAM → Roles → Create role**
- Trusted entity: **AWS service** → **App Runner** → ユースケース **App Runner - Instance**（信頼ポリシーが `tasks.apprunner.amazonaws.com` になる）
- インラインポリシーで以下を許可（Parameter Store 読み取り + 復号）：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ssm:GetParameters", "ssm:GetParameter"],
      "Resource": "arn:aws:ssm:ap-northeast-1:<ACCOUNT_ID>:parameter/ai-shifts/*"
    },
    {
      "Effect": "Allow",
      "Action": "kms:Decrypt",
      "Resource": "*"
    }
  ]
}
```

ロール名は例 `ai-shifts-apprunner-instance` とします。

### 6-2. App Runner サービス作成（コンソール）

コンソール → **App Runner → Create service**

1. **Source**：Container registry → **Amazon ECR** → 第4章で push したイメージ URI（`:latest`）を選択
2. **Deployment settings**：Automatic（ECR に push すると自動再デプロイ）。ECR アクセス用の **Access role** はここで「Create new service role」を選べば自動作成される
3. **Service settings**：
   - Port：**8000**
   - **Environment variables（機密でない値）**：
     - `ENVIRONMENT` = `production`
     - `FRONTEND_ORIGIN` = `https://<CloudFrontのドメイン>`（第8章で確定するので後で更新でも可）
     - `GOOGLE_REDIRECT_URI` = `https://<App RunnerのURL>/api/auth/google/callback`（サービス作成後に確定→更新）
     - `LLM_PROVIDER` = `anthropic`
   - **Environment secrets（Parameter Store 参照）**：Value に **Parameter Store の ARN** を指定
     - `SECRET_KEY` → `arn:aws:ssm:ap-northeast-1:<ACCOUNT_ID>:parameter/ai-shifts/SECRET_KEY`
     - `DATABASE_URL` → `.../ai-shifts/DATABASE_URL`
     - `GOOGLE_CLIENT_ID` → `.../ai-shifts/GOOGLE_CLIENT_ID`
     - `GOOGLE_CLIENT_SECRET` → `.../ai-shifts/GOOGLE_CLIENT_SECRET`
     - `ANTHROPIC_API_KEY` → `.../ai-shifts/ANTHROPIC_API_KEY`
   - **Instance role**：6-1 で作った `ai-shifts-apprunner-instance` を選択
   - **Health check**：まずは **TCP**（ポート 8000 が開いていれば healthy）で OK。HTTP のヘルスパスがあるなら `/` などを指定
4. Create → 数分でデプロイ完了。**Default domain**（`https://xxxx.ap-northeast-1.awsapprunner.com`）が backend の URL。

> ⚠️ **重要**：この Dockerfile の `CMD` は `uvicorn` を起動するだけで、**マイグレーションは実行しません**（compose 版は `alembic upgrade head` を含んでいましたが、App Runner にはその起動コマンドが渡りません）。マイグレーションは次章でローカルから流します。

---

## 7. DB マイグレーション実行（Supabase）

Supabase は Public インターネットから直接接続できるので、**ローカルからそのまま** Alembic を流せます。

```bash
cd backend

DATABASE_URL="postgresql+psycopg://postgres.xxxx:PASSWORD@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres" \
  uv run alembic upgrade head
```

`Running upgrade -> 0001 ...` が出れば成功。Supabase Dashboard → **Database → Tables** でテーブルが作られているのを確認できます。

> 💡 継続運用では「push のたびに手でマイグレーション」は面倒なので、後で CI（GitHub Actions）のデプロイ手順に組み込むのがおすすめです。

---

## 8. フロントを S3 + CloudFront で配信

> 📚**学習メモ：S3 と CloudFront**
> - **S3（Simple Storage Service）** … オブジェクトストレージ。静的ファイル（HTML/JS/CSS）を置ける。耐久性 99.999999999%（イレブンナイン）は試験頻出。
> - **CloudFront** … CDN（世界中のエッジにキャッシュして高速配信）＋ **HTTPS 終端**。S3 を直接公開せず、CloudFront 経由でのみ見せるのが定石（**OAC = Origin Access Control**）。

### 8-1. フロントをビルド

`VITE_API_BASE_URL` を **App Runner の URL** に向けてビルドします。

```bash
cd frontend
VITE_API_BASE_URL="https://xxxx.ap-northeast-1.awsapprunner.com" npm run build
# → dist/ が生成される
```

### 8-2. S3 バケット作成 & アップロード

```bash
REGION=ap-northeast-1
BUCKET=ai-shifts-frontend-<好きな一意な名前>

aws s3 mb s3://$BUCKET --region $REGION
aws s3 sync frontend/dist s3://$BUCKET --delete
```

> バケットは**公開せず**（Block Public Access は ON のまま）、次の CloudFront + OAC 経由でのみ配信します。

### 8-3. CloudFront ディストリビューション作成（コンソール推奨）

コンソール → **CloudFront → Create distribution**
- **Origin**：先ほどの S3 バケットを選択 → **Origin access**：**Origin access control (OAC)** を作成し、表示される **バケットポリシー**を S3 に適用（コンソールがコピー用に出してくれる）
- **Default root object**：`index.html`
- **Viewer protocol policy**：Redirect HTTP to HTTPS
- SPA（Vue Router）用に **エラーページ設定**：`403` と `404` を **`/index.html`（200）** に返すルールを追加（直リンク・リロードで 404 にならないため）

作成後の **Distribution domain name**（`https://xxxx.cloudfront.net`）がフロントの公開 URL です。

---

## 9. OAuth リダイレクト URI と FRONTEND_ORIGIN を更新

URL が確定したので、3か所を揃えます。

1. **Google Cloud Console → OAuth 2.0 クライアント ID**
   - 承認済みリダイレクト URI に `https://<App RunnerのURL>/api/auth/google/callback` を追加
   - 承認済み JavaScript 生成元に `https://<CloudFrontのドメイン>` を追加
2. **App Runner の環境変数**（コンソールで更新 → 再デプロイ）
   - `FRONTEND_ORIGIN` = `https://<CloudFrontのドメイン>`
   - `GOOGLE_REDIRECT_URI` = `https://<App RunnerのURL>/api/auth/google/callback`
3. 変更を保存すると App Runner が自動で再デプロイされます。

> 📚**学習メモ：CORS**
> backend は `FRONTEND_ORIGIN` を許可オリジンとして CORS を設定します。ここが CloudFront ドメインと一致していないと、ブラウザが API 呼び出しをブロックします（`No 'Access-Control-Allow-Origin'` エラー）。

---

## 10. 初回ログインと動作確認

1. `https://<CloudFrontのドメイン>` を開く
2. Google ログインを実行
3. シフト一覧・従業員などが表示されれば成功

うまくいかないときは第13章へ。

---

## 11. 更新・再デプロイ

**backend を更新**（コード変更後）：

```bash
cd backend
docker build --platform linux/amd64 -t ai-shifts-backend .
docker tag ai-shifts-backend:latest <ACCOUNT_ID>.dkr.ecr.ap-northeast-1.amazonaws.com/ai-shifts-backend:latest
docker push <ACCOUNT_ID>.dkr.ecr.ap-northeast-1.amazonaws.com/ai-shifts-backend:latest
# → App Runner が自動再デプロイ（Automatic 設定時）
```

DB スキーマ変更を伴う場合は、push 後に第7章のマイグレーションを再実行。

**frontend を更新**：

```bash
cd frontend
VITE_API_BASE_URL="https://xxxx.ap-northeast-1.awsapprunner.com" npm run build
aws s3 sync dist s3://$BUCKET --delete
# CloudFront のキャッシュを消す（すぐ反映したい時）
aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths "/*"
```

> 💡**次の学習ステップ：GitHub Actions + OIDC**
> 上記の手作業を CI 化できます。**OIDC** を使うと、GitHub に AWS のアクセスキーを保存せずにデプロイできる（キーレス）。IAM の「フェデレーション」を学ぶ良い題材で、試験でも問われます。慣れてきたら挑戦しましょう。

---

## 12. 撤収（teardown）

⚠️ **App Runner は起動しているだけで課金されます。** 学習・検証が終わったら必ず消してください。

1. **App Runner** → サービスを **Delete**（一時的に止めるだけなら **Pause** で課金を抑えられる）
2. **CloudFront** → ディストリビューションを **Disable → Delete**
3. **S3** → `aws s3 rb s3://$BUCKET --force`
4. **ECR** → `aws ecr delete-repository --repository-name ai-shifts-backend --force --region ap-northeast-1`
5. **SSM パラメータ** → `aws ssm delete-parameter --name /ai-shifts/SECRET_KEY`（各パラメータ）
6. **IAM ロール** → 作成した App Runner 用ロールを削除
7. Supabase は無料枠なので残してもゼロ円（不要なら Supabase Dashboard から削除）

---

## 13. トラブルシューティング

| 症状 | 原因 / 対処 |
|---|---|
| App Runner が起動直後に落ちる（Rolled back） | **CloudWatch Logs**（App Runner → サービス → Logs）を確認。多くは DB 接続失敗（`DATABASE_URL` の誤り）か、Parameter Store 読み取り権限不足（Instance role 見直し）。 |
| `exec format error` | Apple Silicon で `--platform linux/amd64` を付けずにビルドした。付け直して push。 |
| `database "..." does not exist` | `DATABASE_URL` の DB 名末尾に余計な文字（改行 `\r` など）が無いか確認。Supabase の接続文字列をコピペし直す。 |
| ブラウザで CORS エラー | `FRONTEND_ORIGIN`（App Runner 環境変数）が CloudFront ドメインと**完全一致**しているか。末尾スラッシュ・http/https の違いに注意。 |
| Google ログイン後 `redirect_uri_mismatch` | Google Console のリダイレクト URI と `GOOGLE_REDIRECT_URI`（App Runner）が一致していない。 |
| フロントでリロードすると 404 | CloudFront の 403/404 → `/index.html`(200) のエラーページ設定を忘れている（第8-3）。 |
| Parameter Store が読めない | Instance role のポリシー Resource が `parameter/ai-shifts/*` を含むか、`kms:Decrypt` があるか確認。 |

---

## 14. 用語集（試験対策）

| 用語 | 意味 |
|---|---|
| **IAM ユーザー / ロール / ポリシー** | 誰が(ユーザー)・何のサービスが(ロール)・何を(ポリシー)できるか |
| **ルートユーザー** | アカウント最強権限。MFA 必須・普段使い禁止 |
| **MFA** | 多要素認証。パスワード＋ワンタイムコード |
| **リージョン / アベイラビリティゾーン(AZ)** | 地理的な場所 / リージョン内の独立したデータセンター群 |
| **VPC / Subnet / Security Group** | 仮想ネットワーク / その区画 / インスタンス単位のファイアウォール（今回は不使用だが必修） |
| **ECR** | Docker イメージのプライベートレジストリ |
| **App Runner** | フルマネージドなコンテナ実行（Cloud Run 相当） |
| **ECS / Fargate** | コンテナオーケストレーション / サーバー管理不要の実行基盤 |
| **Lambda** | サーバーレス関数。ゼロ課金にできる |
| **S3** | オブジェクトストレージ。静的サイトホスティング可 |
| **CloudFront** | CDN + HTTPS 終端。OAC で S3 を保護 |
| **SSM Parameter Store** | 設定・機密の保管（SecureString は無料で暗号化） |
| **Secrets Manager** | 機密特化・自動ローテーション対応（有料） |
| **KMS** | 暗号鍵の管理サービス |
| **CloudWatch** | ログ・メトリクス・アラーム |
| **AWS Budgets** | 予算アラート |
| **IaC / Terraform** | インフラをコードで管理 |
| **OIDC フェデレーション** | 鍵を持たずに外部(GitHub 等)から AWS へ認可 |

---

## 参考：この後の発展課題（学習を深めるなら）

1. **Terraform 化**（`deploy/terraform-aws/`）：本手順の 4〜6・8 章を aws provider で IaC 化。既存の GCP Terraform が良い比較教材。
2. **GitHub Actions + OIDC** による自動デプロイ。
3. **RDS への移行**：Supabase → RDS PostgreSQL に替えると、**VPC / Subnet / Security Group / RDS** という試験の主要範囲を一通り体験できる（App Runner から private RDS へは **VPC Connector** が必要になる）。試験対策としては非常に良い題材。
