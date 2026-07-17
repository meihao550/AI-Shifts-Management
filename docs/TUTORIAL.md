# チュートリアル — 初心者 → 中級者ガイド

このドキュメントは、AI-Shifts-Management プロジェクトを触れるようになることが目的です。

- **前半 (§1–§14)**: プログラミング初心者向け — 全体像・使うツールを掴んで動かす
- **後半 (§15–§28)**: 中級者向け — 実際に機能追加できるようにフレームワーク深掘り・テスト戦略・パフォーマンス・CI/CD
- 対象読者：Web アプリを触ったことはあるが Vue / FastAPI などは初めて → 数週間コードを触ってしっかり書けるようになりたい
- ゴール：機能を安全に追加・改修する PR が書ける
- 所要時間：初回セットアップ 30 分 + 各章 15〜60 分

---

## 目次

### 初心者編

1. [このプロジェクトで何ができるか](#1-このプロジェクトで何ができるか)
2. [開発の全体像を掴む](#2-開発の全体像を掴む)
3. [使うツール一覧と役割](#3-使うツール一覧と役割)
4. [環境構築（Dev Container 版）](#4-環境構築dev-container-版)
5. [とりあえず動かしてみる](#5-とりあえず動かしてみる)
6. [フロントエンド入門: Vue 3 + TypeScript](#6-フロントエンド入門-vue-3--typescript)
7. [バックエンド入門: FastAPI + SQLAlchemy](#7-バックエンド入門-fastapi--sqlalchemy)
8. [DB とマイグレーション（Alembic）](#8-db-とマイグレーションalembic)
9. [CP-SAT による最適化とは？](#9-cp-sat-による最適化とは)
10. [LLM 連携の仕組み](#10-llm-連携の仕組み)
11. [Docker とコンテナ](#11-docker-とコンテナ)
12. [Git とチーム開発](#12-git-とチーム開発)
13. [よくあるエラーと対処](#13-よくあるエラーと対処)
14. [初心者編の次のステップ](#14-初心者編の次のステップ)

### 中級者編

15. [Composition API 深掘り：composables と watch](#15-composition-api-深掘りcomposables-と-watch)
16. [Pinia の使いこなし](#16-pinia-の使いこなし)
17. [FastAPI の依存性注入と非同期](#17-fastapi-の依存性注入と非同期)
18. [SQLAlchemy 2.0 実践：リレーション・N+1 対策](#18-sqlalchemy-20-実践リレーションn1-対策)
19. [Pydantic v2 の型検証・ジェネリクス](#19-pydantic-v2-の型検証ジェネリクス)
20. [Alembic 上級：自動生成の落とし穴と手直し](#20-alembic-上級自動生成の落とし穴と手直し)
21. [CP-SAT モデリング実践](#21-cp-sat-モデリング実践)
22. [LLM プロンプト設計と信頼性](#22-llm-プロンプト設計と信頼性)
23. [テスト戦略](#23-テスト戦略)
24. [デバッグ実践](#24-デバッグ実践)
25. [パフォーマンス最適化](#25-パフォーマンス最適化)
26. [セキュリティのチェックポイント](#26-セキュリティのチェックポイント)
27. [CI / CD の仕組み](#27-ci--cd-の仕組み)
28. [機能追加のフルサイクル演習](#28-機能追加のフルサイクル演習)

---

## 1. このプロジェクトで何ができるか

**目的**：飲食店・小売店など「シフト作成に月 30 分以上かかっている職場」向けに、シフト作成を自動化するアプリです。

具体的には：

- 従業員 25 名くらいの職場を想定
- 各人の「休みたい日」「入りたい日」を入力
- AI が労働時間や必要人数を守りながら 1 か月分のシフトを自動生成
- 「田中さんは 8/15 に夏休み」「8/20 は繁忙期なので朝を +1 人」など、**自然言語で追加ルールを書ける**
- 生成されたシフトから、人件費・保険加入判定・PDF や Excel 出力まで
- Google アカウントでログイン、管理者と一般社員でできることが分かれる

**なぜ AI と最適化（CP-SAT）の両方使うの？**

- **AI（LLM）**：人間の言葉「今週の金曜日は繁忙期」を機械が使える形（JSON）に変換
- **CP-SAT**：「全員の希望を可能な限り叶えつつ必要人員も満たす組み合わせ」を数学的に解く
- 役割を分担することで、AI に丸投げより速く・正確に・破綻なくシフトが作れる

---

## 2. 開発の全体像を掴む

このアプリは **フロントエンド** と **バックエンド** に分かれています。

```
   ユーザ (ブラウザ)
        │
        │ ①URLを開く／ボタンを押す
        ▼
  ┌─────────────────┐
  │  フロントエンド  │  Vue 3 で作った SPA（Single Page App）
  │  (Vue 3)        │  画面表示、ボタン、入力フォームなど
  └────────┬────────┘
           │
           │ ②APIを叩く (HTTP JSON)
           ▼
  ┌─────────────────┐
  │  バックエンド    │  FastAPI で作った API サーバ
  │  (FastAPI)      │  DB 読み書き、シフト生成、認証
  └────────┬────────┘
           │
           │ ③SQLでデータ保存
           ▼
  ┌─────────────────┐
  │  データベース    │  PostgreSQL
  │  (PostgreSQL)   │  従業員・シフト・ルールなど
  └─────────────────┘
```

- **フロントエンド** ＝ 見た目・使い勝手 を担当（HTML / CSS / JS の進化版）
- **バックエンド** ＝ 計算・データ保存 を担当（Python サーバ）
- **DB** ＝ 情報を永続化する場所（Excel の巨大版みたいなもの）

この 3 つが別々のプロセスで動き、HTTP で通信します。

---

## 3. 使うツール一覧と役割

初めて見る名前が多いと思うので、**「何のためのツールか」だけ**まず押さえてください。

### 言語

| ツール | 何のため | 補足 |
|---|---|---|
| **TypeScript** | フロント開発 | JavaScript に「型」を足したもの。`age: number` のように書く |
| **Python** | バック開発 | データ処理・機械学習・Web にも強い汎用言語 |
| **SQL** | DB 操作 | 「このテーブルからこの条件のデータを取り出す」を書く |

### フロントエンドで使うもの

| ツール | 役割 |
|---|---|
| **Vue 3** | 画面を作るフレームワーク（React と兄弟） |
| **Vite** | 開発サーバ + ビルドツール（超速い） |
| **Vue Router** | 「/dashboard」「/shift」などページ切り替え |
| **Pinia** | ログイン情報など画面をまたぐデータを保持する箱 |
| **Naive UI** | ボタン・表・カレンダーなど部品集 |
| **axios** | バックエンドの API を叩く HTTP クライアント |

### バックエンドで使うもの

| ツール | 役割 |
|---|---|
| **FastAPI** | API サーバフレームワーク。Swagger UI が自動で作られる |
| **Pydantic** | データの形を定義して検証。「name は文字列、age は 15〜99」など |
| **SQLAlchemy** | Python から SQL を生成する。テーブルをクラスとして書ける |
| **Alembic** | DB のスキーマ変更履歴を管理（ファイルシステム版 Git みたいな） |
| **OR-tools CP-SAT** | 制約充足問題（＝パズル）を解くソルバ。シフト作成に使う |
| **JPHoliday** | 日本の祝日判定 |
| **openpyxl / reportlab** | Excel / PDF 生成 |
| **Anthropic / OpenAI SDK** | LLM を呼ぶための公式ライブラリ |

### 開発を支えるもの

| ツール | 役割 |
|---|---|
| **Docker / Docker Compose** | アプリを「箱（コンテナ）」に閉じ込めて、どの PC でも同じように動かす |
| **Dev Container** | VS Code で Docker を開発環境として使う機能 |
| **uv** | Python の高速パッケージマネージャ（pip の高速版） |
| **npm** | Node.js のパッケージマネージャ |
| **Ruff** | Python の Lint + Format（ミスチェック + 見た目整形） |
| **mypy** | Python の型チェッカー |
| **ESLint** | TS/JS の Lint |
| **Prettier** | JS/TS/Vue の Format |
| **Pytest** | Python のテストランナー |
| **Vitest** | TS のテストランナー |
| **Git** | ソースコードの変更履歴管理 |
| **GitHub Actions** | プッシュ時に自動でテスト実行（CI） |

### インフラ / デプロイ

| ツール | 役割 |
|---|---|
| **Supabase** | Postgres の無料ホスティング |
| **Google Cloud Run** | Docker コンテナを実行する「無料枠つき」サーバ |
| **Terraform** | インフラをコード化するツール（GUI ぽちぽち作業を撲滅） |
| **Google OAuth** | Google アカウントでログインする仕組み |

---

## 4. 環境構築（Dev Container 版）

「Node のバージョンが違う」「Python が動かない」問題を避けるため、**Dev Container** を使います。

### 4-1. 必要なもの

1. **VS Code** をインストール
   https://code.visualstudio.com/
2. **Docker Desktop** をインストールして起動
   https://www.docker.com/products/docker-desktop/
3. VS Code に **Dev Containers 拡張機能** を入れる
   - 左サイドバーの拡張機能アイコンから `Dev Containers` を検索してインストール

### 4-2. リポジトリを開く

```bash
# 好きな場所に clone
git clone https://github.com/meihao550/AI-Shifts-Management.git
cd AI-Shifts-Management

# VS Code で開く
code .
```

### 4-3. Dev Container を起動

- VS Code 画面右下に **「Reopen in Container」** の通知が出るので **クリック**
- 出ないときは：`Cmd+Shift+P`（Mac）または `Ctrl+Shift+P`（Windows/Linux） → **Dev Containers: Reopen in Container**
- 初回は Docker イメージのビルドで **5〜10 分**かかります。コーヒーでも。
- 起動後、VS Code のターミナル（`` Cmd+` ``）はコンテナ内に接続されています

### 4-4. 動作確認

コンテナ内のターミナルで：

```bash
# Python バージョン確認
python --version   # → Python 3.11.x
# Node バージョン確認
node --version     # → v20.x.x
# Terraform / gcloud も入ってる
terraform version
gcloud --version
```

---

## 5. とりあえず動かしてみる

Dev Container が立ち上がった状態で、**バックエンド → フロントエンド** の順に起動します。

### 5-1. バックエンド起動

```bash
cd backend
uv run alembic upgrade head          # DB テーブル作成（初回のみ）
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- 初回は依存パッケージのダウンロードで少し時間かかります
- 起動したら http://localhost:8000/docs にブラウザでアクセス
- **Swagger UI** が表示されて、API が全部一覧できます。試しに `/api/health` を Try it out で叩いてみる

### 5-2. フロントエンド起動（別ターミナル）

```bash
cd frontend
npm install    # 初回のみ
npm run dev -- --host 0.0.0.0
```

- http://localhost:5173 にアクセス
- ログイン画面が表示されます
- 「開発用ログイン」ボタンで即入れます（初回は自動的に admin になる）

### 5-3. サンプルデータ投入

初回はデータが空なので、ログイン画面の **「サンプルデータ投入 (25 名分)」** ボタンを押してください。従業員 25 名 + シフトパターン + 必要人員が入ります。

### 5-4. シフト作成を試す

1. ログイン → ヘッダの **「シフト表」** をクリック
2. カレンダーで従業員を選び、「休日」「希望日」を数個クリックして登録
3. 「AI シフト生成」欄で「シフトを生成」ボタン
4. 数秒後にシフト表がずらっと埋まる → 完成！
5. **「人件費」** ページで月次コスト、**「印刷プレビュー」** で PDF/Excel 出力も試せる

---

## 6. フロントエンド入門: Vue 3 + TypeScript

### 6-1. Vue の 「コンポーネント」 とは

Vue は「画面を小さな部品（コンポーネント）に分けて作る」フレームワークです。

1 つのコンポーネントは **`.vue` ファイル 1 つ** で、3 つのブロックからなります：

```vue
<!-- HelloWorld.vue -->
<script setup lang="ts">
// ① ロジック（TypeScript）
import { ref } from 'vue'
const count = ref(0)          // リアクティブな数値
const increment = () => count.value++
</script>

<template>
  <!-- ② 見た目（HTML拡張） -->
  <button @click="increment">
    押した回数: {{ count }}
  </button>
</template>

<style scoped>
/* ③ CSS（scoped でこのコンポーネントだけに適用） */
button { font-size: 20px; }
</style>
```

- `ref()`：値を Vue が監視できる形にする（変わったら画面が自動更新）
- `@click="increment"`：クリックしたら関数を呼ぶ
- `{{ count }}`：波括弧 2 個で変数を画面に埋め込み
- `<style scoped>`：この CSS はこのコンポーネントの中でだけ効く

### 6-2. このプロジェクトのフロント構造

```
frontend/src/
├── main.ts          # アプリの起動地点
├── App.vue          # 一番外側のコンポーネント（全画面の枠）
├── router/          # URL → 画面の対応表
├── stores/          # Pinia。ログイン状態などのグローバルな箱
├── views/           # 画面（ページ）単位のコンポーネント
├── components/      # 画面内の部品（カレンダー、ヘッダなど）
├── api/             # バックエンドと話すクライアント
└── types/           # TypeScript の型定義
```

例えば、`ShiftTableView.vue` を開くと：

```vue
<script setup lang="ts">
import { useShiftStore } from '@/stores/shift'
const shift = useShiftStore()

async function generate() {
  await shift.generate({ year: 2026, month: 7 })
}
</script>

<template>
  <button @click="generate">シフト生成</button>
</template>
```

- `useShiftStore()`：Pinia でシフト情報を扱う store を取得
- `shift.generate(...)`：バックエンドの `/api/shifts/generate` を叩く関数（`stores/shift.ts` の中で axios を呼んでいる）

### 6-3. TypeScript の見方

「JavaScript に型を足しただけ」ですが、慣れないと最初は面倒に感じるかも。

```ts
// これだけ知ってれば大体読める
const name: string = '田中'          // 文字列
const age: number = 30               // 数値
const active: boolean = true         // 真偽値
const emails: string[] = ['a@x.jp']  // 文字列の配列

interface Employee {                 // 型の定義
  id: number
  name: string
  age: number | null                 // number または null
  email?: string                     // ? は省略可
}

function greet(emp: Employee): string {
  return `こんにちは ${emp.name}`
}
```

### 6-4. Naive UI の使い方

`<NButton>`, `<NDataTable>`, `<NDatePicker>` などをそのまま書けば使えます。ドキュメントは https://www.naiveui.com/en-US/os-theme/components/button

---

## 7. バックエンド入門: FastAPI + SQLAlchemy

### 7-1. FastAPI の 「ルーター」 とは

「/api/employees にアクセスされたときにどんな処理をするか」を書くのがルーター。

```python
# app/routers/employees.py
from fastapi import APIRouter

router = APIRouter(prefix="/employees", tags=["employees"])

@router.get("")                        # GET /employees
def list_employees():
    return [{"name": "田中"}]

@router.post("")                       # POST /employees
def create_employee(payload: EmployeeCreate):
    # payload は自動で JSON → Python オブジェクトに変換される
    return {"created": True}
```

### 7-2. Pydantic スキーマとは

「API がやり取りするデータの形」を定義するクラス。

```python
# app/schemas/employee.py
from pydantic import BaseModel, Field

class EmployeeCreate(BaseModel):
    name: str
    age: int | None = Field(default=None, ge=15, le=99)
    hourly_wage: int = Field(default=1100, ge=0)
```

これで API に不正なデータが来たら自動で 422 エラーを返してくれる。

### 7-3. SQLAlchemy モデルとは

DB のテーブルを Python のクラスで表す。

```python
# app/models/employee.py
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    hourly_wage: Mapped[int] = mapped_column(Integer, default=1100)
```

これに対して SQL を書かずに操作できる：

```python
# 全件取得
employees = db.execute(select(Employee)).scalars().all()

# 追加
db.add(Employee(name="田中", hourly_wage=1200))
db.commit()

# 更新
emp = db.get(Employee, 1)
emp.hourly_wage = 1300
db.commit()

# 削除
db.delete(emp)
db.commit()
```

### 7-4. データの流れ

```
ブラウザ → axios → FastAPI ルーター → Pydantic 検証 → サービス層 → SQLAlchemy → PostgreSQL
                                                                  ↑
                          レスポンスは逆に PostgreSQL → SQLAlchemy → Pydantic → JSON → ブラウザ
```

---

## 8. DB とマイグレーション（Alembic）

### 8-1. マイグレーションとは

「DB のスキーマ（テーブル構造）の変更履歴」をファイルで管理する仕組み。

- モデル（`app/models/*.py`）を変えたら → マイグレーションを生成 → DB に適用
- チーム全員が同じスキーマになる。過去に戻せる

### 8-2. 新しいテーブルを追加する流れ

```bash
# 1. モデルを追加/編集（例: app/models/xxx.py）

# 2. マイグレーション自動生成
cd backend
uv run alembic revision --autogenerate -m "add xxx table"

# 3. 生成されたファイル alembic/versions/xxxx.py を確認

# 4. DB に適用
uv run alembic upgrade head

# 5. 元に戻したい場合
uv run alembic downgrade -1
```

---

## 9. CP-SAT による最適化とは？

**シフト作成**は「制約充足問題」＝パズルです。

- **変数**: 各従業員 × 各日 × 各シフト種別 の割当（0 か 1）
- **ハード制約**（絶対守る）:
  - 各シフトに必要人数ぴったり
  - 「勤務不可日」は絶対 0
  - 1 人 1 日 1 シフトまで
- **ソフト制約**（できるだけ守る）:
  - 週の勤務回数を希望値に近づける
  - 「入りたい日」はできるだけ入れる

CP-SAT はこれを **数秒で最適解を見つけて**くれます。実装は `backend/app/services/scheduler.py` を参照。

```python
model = cp_model.CpModel()

# 変数を作る
x = {}
for emp in employees:
    for day in days:
        for pattern in patterns:
            x[emp, day, pattern] = model.NewBoolVar(f"x_{emp}_{day}_{pattern}")

# 制約: 各シフトの必要人数
for day, cat in ...:
    model.Add(sum(x[emp, day, p] for emp, p ...) == required)

# 目的関数: ソフト制約の合計を最小化
model.Minimize(deviation_terms - preference_bonus)

# 解く
solver = cp_model.CpSolver()
status = solver.Solve(model)
```

---

## 10. LLM 連携の仕組み

「今月の事情」を自然言語で入力すると、LLM が JSON の制約に変換します。

### 10-1. プロンプト設計

```python
SYSTEM_PROMPT = """
あなたはシフトスケジューリングの制約抽出アシスタントです。
以下のスキーマに厳密に一致する JSON のみ出力してください。

{
  "hard_unavailable": [{"employee_id": <int>, "date": "YYYY-MM-DD"}],
  "max_shifts_per_week_override": {"<id>": <int>},
  ...
}
"""
```

これを Anthropic Claude または OpenAI に投げて、返ってきた JSON を Python の dict にパースして CP-SAT に渡します。

### 10-2. なぜスキーマを固定？

LLM は自由に文章を書くので、スキーマを厳密に指定しないと後段でエラーになる。**System prompt でスキーマを明示 + `response_format={"type":"json_object"}` を指定**することで、必ず有効な JSON を返してもらえます。

### 10-3. コード

`backend/app/services/llm.py` を参照。プロバイダは `LLM_PROVIDER` 環境変数で切り替え。

---

## 11. Docker とコンテナ

### 11-1. なぜ Docker？

「私の PC では動くのにあなたの PC では動かない」問題を解決。**アプリと OS・言語・ライブラリを 1 個の箱に詰めて配布**する仕組みです。

### 11-2. このプロジェクトでの構成

`docker-compose.yml` に 3 つのサービスが定義されています：

```yaml
services:
  db:        # PostgreSQL
  backend:   # FastAPI
  frontend:  # Vite dev server
```

### 11-3. 主要コマンド

```bash
docker compose up         # 全部起動（Ctrl+C で終了）
docker compose up -d      # バックグラウンド起動
docker compose down       # 停止 + コンテナ削除
docker compose logs backend       # backend のログ
docker compose exec backend bash  # backend の中に入る
docker compose build --no-cache backend  # 強制再ビルド
```

### 11-4. Dockerfile とは

「コンテナの中身を作るレシピ」。`backend/Dockerfile` は：

```dockerfile
FROM python:3.11-slim         # ベースイメージ
WORKDIR /app                  # 作業ディレクトリ
COPY pyproject.toml ./        # 依存定義をコピー
RUN pip install -e ".[dev]"   # インストール
COPY . .                      # 全ソースをコピー
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]  # 起動コマンド
```

---

## 12. Git とチーム開発

### 12-1. 基本フロー

```bash
# 最新の main を取ってくる
git checkout main
git pull origin main

# 作業用ブランチを切る
git checkout -b feat/add-something

# コードを書く…

# 変更を確認
git status
git diff

# ステージング → コミット
git add backend/app/routers/xxx.py
git commit -m "feat(backend): 従業員検索 API を追加"

# プッシュ
git push -u origin feat/add-something

# GitHub で Pull Request を作る
gh pr create --title "..." --body "..."
```

### 12-2. コミットメッセージの型（Conventional Commits）

```
<type>(<scope>): <subject>

feat: 新機能
fix: バグ修正
docs: ドキュメント
style: 見た目だけ
refactor: 挙動変わらない書き換え
test: テスト
chore: それ以外
```

### 12-3. PR ルール

- ブランチ名: `feat/xxx`, `fix/xxx`, `docs/xxx`
- PR タイトルもコミットメッセージ形式
- 説明に「何を」「なぜ」「テスト方法」を書く
- CI が通ってから review 依頼

---

## 13. よくあるエラーと対処

### `ModuleNotFoundError: No module named 'app'`

**原因**: バックエンドディレクトリ以外から起動している
**対処**: `cd backend` してから `uv run uvicorn ...`

### `EADDRINUSE :5173`

**原因**: ポートが他プロセスで使用中
**対処**:
```bash
lsof -i :5173     # 何が使ってるか確認
kill <PID>        # 該当プロセスを止める
```

### `alembic upgrade head` で `target database is not up to date`

**原因**: マイグレーション履歴の食い違い
**対処**:
```bash
uv run alembic history       # 履歴確認
uv run alembic current       # 現在のバージョン確認
uv run alembic downgrade -1  # 一つ戻る
uv run alembic upgrade head  # 再適用
```

### `ネットワークエラー / CORS エラー`

**原因**: backend が起動していない、または `FRONTEND_ORIGIN` が間違い
**対処**:
- backend の `docker compose logs backend` を確認
- `.env` の `FRONTEND_ORIGIN=http://localhost:5173` を確認

### `TypeError: Cannot read properties of undefined`

**原因**: フロントで `data.foo` の `data` がまだ undefined
**対処**: `v-if="data"` で守るか、`?.` オプショナルチェイニングを使う

### Docker が遅い / メモリ不足

**対処**: Docker Desktop → Settings → Resources で Memory を 4GB → 8GB に増やす

---

## 14. 初心者編の次のステップ

初心者編を読み終えたら中級者編（§15 以降）に進んでください。中級者編は「実際に機能追加できる」ことをゴールにしています。

先に軽く手を動かすなら以下がオススメ：
- `frontend/src/views/DashboardView.vue` の見た目を少し変えてみる
- `backend/tests/test_payroll.py` に新しいテストケースを追加
- Naive UI のドキュメントを見ながら新しい部品を試す

---

# 中級者編

ここからは「動かせる → 触れる」から「**安全に機能追加できる**」を目指します。

---

## 15. Composition API 深掘り：composables と watch

### 15-1. `ref` / `reactive` / `computed` の違い

```ts
import { ref, reactive, computed } from 'vue'

// ref: プリミティブでも配列でもOK。値へのアクセスは .value 必須。
const count = ref(0)
count.value++

// reactive: オブジェクトだけ。プロパティに直アクセスできる。
const state = reactive({ name: '田中', age: 30 })
state.age = 31

// computed: 依存が変わったときだけ再計算されるキャッシュ付き値
const doubled = computed(() => count.value * 2)
```

**使い分けの目安**:
- 単一値・プリミティブ → `ref`
- ドメインの塊（フォーム全体、設定オブジェクト） → `reactive`
- 派生値 → `computed`

**注意点**: `reactive` オブジェクトを分割代入すると反応性が壊れます。
```ts
const state = reactive({ count: 0 })
const { count } = state   // ← 反応性がここで切れる
```
分割代入したいときは `toRefs()` を使う。

### 15-2. watch と watchEffect

`watch`: 特定の値を監視して変化時にコールバック。
```ts
import { watch } from 'vue'

watch(count, (newV, oldV) => {
  console.log(`${oldV} → ${newV}`)
})

// 複数を監視
watch([count, name], ([nc, nn]) => { ... })

// deep モード（オブジェクト内部の変更も検知）
watch(() => state, () => { ... }, { deep: true })

// immediate: 初回にも実行
watch(count, cb, { immediate: true })
```

`watchEffect`: 使った reactive 値を自動追跡。
```ts
import { watchEffect } from 'vue'

watchEffect(() => {
  // count と name のどちらかが変わったら再実行
  console.log(`${name.value} = ${count.value}`)
})
```

### 15-3. composable を自作する

「複数コンポーネントで共有したいロジック」を関数に切り出す。慣習として `use~` プレフィックス。

```ts
// composables/useCounter.ts
import { ref, computed } from 'vue'

export function useCounter(initial = 0) {
  const count = ref(initial)
  const doubled = computed(() => count.value * 2)
  const increment = () => count.value++
  const reset = () => (count.value = initial)
  return { count, doubled, increment, reset }
}
```

コンポーネントから使う：
```ts
const { count, doubled, increment } = useCounter(10)
```

本プロジェクトの例: `useShiftStore` は Pinia の store だが、動作原理は composable と同じ (store 自体が composition function)。

### 15-4. lifecycle フック

`<script setup>` 内で使える主なフック：
| フック | タイミング |
|---|---|
| `onMounted` | DOM に描画された直後 |
| `onUpdated` | 更新後 |
| `onBeforeUnmount` | 破棄前（listener 解除等） |
| `onErrorCaptured` | 子孫コンポーネントのエラーを捕捉 |

```ts
import { onMounted, onBeforeUnmount } from 'vue'

onMounted(() => {
  window.addEventListener('resize', handler)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', handler)
})
```

---

## 16. Pinia の使いこなし

### 16-1. store の定義パターン

このプロジェクトは Options 記法を使用：
```ts
// stores/shift.ts
export const useShiftStore = defineStore('shift', {
  state: () => ({ shift: null as Shift | null }),
  getters: {
    total: (s) => s.shift?.assignments.length ?? 0,
  },
  actions: {
    async fetch(year: number, month: number) { ... },
  },
})
```

Composition 記法（同等）:
```ts
export const useShiftStore = defineStore('shift', () => {
  const shift = ref<Shift | null>(null)
  const total = computed(() => shift.value?.assignments.length ?? 0)
  async function fetch(year: number, month: number) { ... }
  return { shift, total, fetch }
})
```

好みで OK ですが、既存に合わせて Options 記法を継続するのが無難。

### 16-2. store 間の呼び出し

```ts
// stores/employee.ts
import { useAuthStore } from './auth'

export const useEmployeeStore = defineStore('employee', {
  actions: {
    async fetchMine() {
      const auth = useAuthStore()   // ← action の中で呼ぶ
      return await api.get(`/employees/${auth.user?.employee_id}`)
    },
  },
})
```

**注意**: setup の外 (モジュールのトップレベル) で `useXxxStore()` を呼ぶと、Pinia がまだ初期化されていない可能性がある。必ず setup / action / composable 内で呼ぶ。

### 16-3. リセットと永続化

```ts
// 全 state を初期状態にリセット
store.$reset()

// 特定のフィールドだけ patch
store.$patch({ shift: null })

// 変更検知
store.$subscribe((mutation, state) => {
  localStorage.setItem('shift-state', JSON.stringify(state))
})
```

永続化ライブラリ (`pinia-plugin-persistedstate`) を入れると自動化できる。

### 16-4. ストア設計のガイドライン

- **1 ドメイン 1 ストア**（auth / shift / employee / rule）
- state は正規化する（`employees` を配列で持ちつつ `employeeById` computed）
- API 呼び出しは action にまとめて、component から直接 axios は避ける

---

## 17. FastAPI の依存性注入と非同期

### 17-1. Depends の連鎖

```python
def get_db() -> Session: ...
def get_current_user(token=Depends(oauth2), db=Depends(get_db)): ...
def require_admin(user=Depends(get_current_user)): ...

@router.get("/admin")
def admin_only(user=Depends(require_admin)): ...
```

依存関係は **DAG（有向非巡回グラフ）** として解決され、同じ依存は 1 リクエスト内で 1 回しか呼ばれない（キャッシュ）。

### 17-2. Annotated 記法（推奨）

```python
from typing import Annotated
CurrentUser = Annotated[User, Depends(get_current_user)]

@router.get("/me")
def me(user: CurrentUser): ...
```

型エイリアス化で再利用しやすい。本プロジェクトは `app/auth/deps.py` で採用。

### 17-3. 同期 vs 非同期エンドポイント

```python
# 同期（別スレッドで実行される）
@router.get("/sync")
def sync_ep(db: Session = Depends(get_db)):
    return db.query(Employee).all()

# 非同期（イベントループ上）
@router.get("/async")
async def async_ep():
    async with httpx.AsyncClient() as client:
        r = await client.get("https://api.example.com")
    return r.json()
```

**選び方**:
- I/O 待ちが長い外部 API → `async def` + `httpx.AsyncClient`
- DB アクセスだけ → `def`（SQLAlchemy の同期 API を素直に使う方が楽）
- 混在するな → 統一する（`async` 内で同期 DB を呼ぶと event loop がブロック）

### 17-4. BackgroundTasks

重い処理をレスポンス後に走らせる：
```python
@router.post("/shifts/generate")
def generate(bt: BackgroundTasks):
    bt.add_task(send_notification_email, ...)
    return {"status": "queued"}
```

**制限**: プロセス内実行なので、Cloud Run のような自動スケーリング環境では、リクエスト完了後インスタンスが落ちるとタスクも消える。長時間タスクは Cloud Tasks / Pub/Sub を検討。

### 17-5. ミドルウェアと例外ハンドラ

```python
@app.middleware("http")
async def add_process_time(request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(time.time() - start)
    return response

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(status_code=400, content={"detail": str(exc)})
```

---

## 18. SQLAlchemy 2.0 実践：リレーション・N+1 対策

### 18-1. リレーションの定義

```python
class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    assignments: Mapped[list["ShiftAssignment"]] = relationship(
        back_populates="employee"
    )

class ShiftAssignment(Base):
    __tablename__ = "shift_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    employee: Mapped["Employee"] = relationship(back_populates="assignments")
```

### 18-2. N+1 問題と解決

**悪い例**:
```python
employees = db.execute(select(Employee)).scalars().all()
for e in employees:
    print(len(e.assignments))   # 各ループごとに追加クエリ
```

**修正**: `selectinload` で一括ロード。
```python
from sqlalchemy.orm import selectinload

stmt = select(Employee).options(selectinload(Employee.assignments))
employees = db.execute(stmt).scalars().all()
for e in employees:
    print(len(e.assignments))   # 追加クエリなし
```

**種類**:
- `selectinload`: 別クエリで IN 句、行数少ないなら◎
- `joinedload`: JOIN、多重リレーションで爆発しがち
- `contains_eager`: 明示的 JOIN + eager load
- `raiseload`: アクセス時に例外（N+1 検出に使える）

### 18-3. 集計クエリ

```python
from sqlalchemy import func

stmt = (
    select(
        Employee.id,
        Employee.name,
        func.count(ShiftAssignment.id).label("shifts"),
    )
    .outerjoin(ShiftAssignment)
    .group_by(Employee.id)
    .order_by(func.count(ShiftAssignment.id).desc())
)
rows = db.execute(stmt).all()   # 行は (id, name, shifts) の namedtuple
```

### 18-4. トランザクション管理

```python
# 明示的トランザクション
with db.begin():
    db.add(x)
    db.add(y)
    # 例外なら自動 rollback、成功なら commit

# 手動
try:
    db.add(x)
    db.commit()
except:
    db.rollback()
    raise
```

FastAPI + Session の場合、通常はリクエスト単位でセッション生成 → close する仕組み（`get_db` の finally）で十分。

### 18-5. Raw SQL が必要なとき

```python
from sqlalchemy import text

rows = db.execute(
    text("SELECT * FROM employees WHERE hourly_wage > :min"),
    {"min": 1200},
).all()
```

Raw SQL でも常に **バインドパラメータ** を使う（文字列連結は SQL Injection の温床）。

---

## 19. Pydantic v2 の型検証・ジェネリクス

### 19-1. Field で追加バリデーション

```python
from pydantic import BaseModel, Field, EmailStr

class EmployeeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=15, le=99)
    email: EmailStr
    hourly_wage: int = Field(default=1100, ge=0)
```

### 19-2. validator / model_validator

```python
from pydantic import model_validator, field_validator

class TimeRange(BaseModel):
    start: time
    end: time

    @field_validator("end")
    def end_after_start(cls, v, info):
        if info.data.get("start") and v <= info.data["start"]:
            raise ValueError("end must be after start")
        return v

    @model_validator(mode="after")
    def check_within_business_hours(self):
        # 全フィールド確定後にモデル全体を検証
        if self.start < time(6, 0):
            raise ValueError("start must be after 06:00")
        return self
```

### 19-3. Config / from_attributes

```python
class EmployeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)   # SQLAlchemy モデルから .model_validate() 可
    id: int
    name: str
```

### 19-4. Generic モデル

```python
from typing import Generic, TypeVar
T = TypeVar("T")

class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int

# 使い方
class EmployeePage(Paginated[EmployeeRead]): pass
```

---

## 20. Alembic 上級：自動生成の落とし穴と手直し

### 20-1. autogenerate が検出できないもの

- カラム名変更（drop + add に見える → データ消失リスク）
- サーバサイド default の変更
- チェック制約変更
- 一部のインデックスオプション

生成後は必ず目視レビューし、上記に該当したら手動修正。

### 20-2. データマイグレーション

スキーマ変更と一緒にデータを移す場合：

```python
# alembic/versions/xxxx_split_name.py
def upgrade():
    op.add_column("employees", sa.Column("first_name", sa.String(50)))
    op.add_column("employees", sa.Column("last_name", sa.String(50)))

    # データ移行
    conn = op.get_bind()
    conn.execute(text("""
        UPDATE employees
        SET first_name = split_part(name, ' ', 1),
            last_name  = split_part(name, ' ', 2)
    """))

    op.drop_column("employees", "name")
```

### 20-3. マージ / 競合

複数人が同時にマイグレーションを追加すると `head` が 2 つになる：

```bash
alembic history         # 分岐を確認
alembic merge -m "merge heads" <head1> <head2>
```

生成されたマージファイルはシンプルに 2 つを親に持つだけ。

### 20-4. downgrade は真面目に書く

`op.drop_column` などの逆操作を書いておくと本番事故時にロールバックできる。破壊的なら手動で「復旧不可」とコメント付ける。

---

## 21. CP-SAT モデリング実践

### 21-1. 基本形

```python
from ortools.sat.python import cp_model

model = cp_model.CpModel()

# 決定変数
x = model.NewBoolVar("x")
y = model.NewIntVar(0, 10, "y")

# 制約
model.Add(x + y >= 3)              # 線形制約
model.AddImplication(x, y > 5)     # x=True なら y>5
model.AddBoolOr([a, b, c])         # OR

# 目的関数
model.Minimize(y - 2 * x)

# 求解
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 20
status = solver.Solve(model)

# 状態確認
if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    print(solver.Value(x), solver.Value(y))
```

### 21-2. ハード制約と ソフト制約の設計

- **ハード**: `model.Add(constraint)` で必ず満たす
- **ソフト**: 「違反ペナルティ変数」を用意して目的関数に加える

本プロジェクトの例（`scheduler.py`）：
```python
# ソフト: 週の希望回数からのずれを最小化
over = model.NewIntVar(0, 31, f"over_{emp.id}")
under = model.NewIntVar(0, 31, f"under_{emp.id}")
model.Add(actual_total - target == over - under)
penalties.append(over)
penalties.append(under)

# 目的関数
model.Minimize(sum(penalties) - 3 * sum(bonus_terms))
```

### 21-3. 無限ループ / INFEASIBLE 対策

- 制約を段階的に足して、どれで INFEASIBLE になるか特定
- `solver.SufficientAssumptionsForInfeasibility()` で無矛盾集合を出力
- タイムアウトを短めから始める（`max_time_in_seconds`）

### 21-4. パフォーマンスチューニング

- 変数を減らす（対称性を利用）
- `num_search_workers` を 4〜8 に
- Warm start（前回解を提示）→ `solver.Solve(model, hint)`

---

## 22. LLM プロンプト設計と信頼性

### 22-1. スキーマ厳密化

自由文出力させると parse エラーの温床。JSON スキーマを system prompt で固定。

```python
SYSTEM_PROMPT = """
以下のスキーマに一致する JSON のみ出力してください。
Markdown コードフェンス不要。前後の説明も不要。

{
  "hard_unavailable": [{"employee_id": <int>, "date": "YYYY-MM-DD"}],
  ...
}
"""
```

**OpenAI**: `response_format={"type": "json_object"}` を使うとさらに安全。
**Anthropic**: system prompt で明示 + Assistant プレフィックス `{`（強制的に JSON 開始）。

### 22-2. パースの防御

```python
def _parse_json(text: str) -> dict:
    text = text.strip()
    # code fence を除去
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[1].rstrip("`").rstrip()
    return json.loads(text)
```

`json.JSONDecodeError` を必ず try/except で捕捉して、失敗時はデフォルト値を返す（本プロジェクトは空 dict）。

### 22-3. リトライとフォールバック

- 1 回目失敗 → 「JSON のみ返してください」を追加してリトライ
- それでも失敗 → 空制約でスケジューラを走らせる（システム全体は動く）
- ユーザに warning として提示

### 22-4. コスト管理

- token 制限: `max_tokens=1500` など指定
- ログに実費見積を書く（プロンプト長 × 単価）
- キャッシュ: 同じ入力→同じ出力ならリクエストしない

---

## 23. テスト戦略

### 23-1. テストピラミッド

```
        E2E (少ない、遅い、壊れやすい)
       ─────
     統合 (数十、DB込み)
    ────────
  単体 (大量、速い、純関数)
```

本プロジェクトの現状：
- 単体: `test_payroll.py`, `test_holidays.py` — 純関数のみで OK
- 統合: これから拡充する余地大（TestClient + テスト用 DB）
- E2E: Playwright / Cypress で検討

### 23-2. Pytest フィクスチャ

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine

@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def client(db_engine):
    return TestClient(app)
```

使い方：
```python
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
```

### 23-3. パラメトライズ

```python
@pytest.mark.parametrize("hours,expected", [
    (79, "none"),
    (80, "employment"),
    (119, "employment"),
    (120, "social"),
])
def test_insurance(hours, expected):
    assert classify_insurance(hours) == expected
```

境界値を系統的に確認できる。

### 23-4. Vitest（フロント）

```ts
// src/composables/__tests__/useCounter.spec.ts
import { describe, it, expect } from 'vitest'
import { useCounter } from '../useCounter'

describe('useCounter', () => {
  it('increments', () => {
    const { count, increment } = useCounter()
    increment()
    expect(count.value).toBe(1)
  })
})
```

コンポーネントのマウントテスト：
```ts
import { mount } from '@vue/test-utils'
import ShiftTable from '@/views/ShiftTableView.vue'

it('renders', () => {
  const wrapper = mount(ShiftTable, { global: { plugins: [pinia, router] } })
  expect(wrapper.text()).toContain('シフト表')
})
```

### 23-5. モックの原則

- **外部依存だけモック**（LLM API、Google OAuth）
- **DB はモックしない**（実 DB に近い挙動を確認）
- モックしすぎると「実装を検証するテスト」になり、リファクタで壊れる

---

## 24. デバッグ実践

### 24-1. Backend

```python
# ログ
import logging
logger = logging.getLogger(__name__)
logger.info("payload=%s", payload)

# デバッガ
import pdb; pdb.set_trace()   # 停止して interactive

# より新しい: breakpoint() でも同じ
breakpoint()
```

VS Code の Python 拡張なら `launch.json` で uvicorn プロセスにアタッチできる。

### 24-2. Frontend

- ブラウザ DevTools の Vue タブ（Volar 拡張）
- Console でリアクティブ値を追う: `console.log(store.$state)`
- Network タブで API リクエストを確認

### 24-3. SQL デバッグ

```python
# SQLAlchemy が発行する SQL を全部表示
engine = create_engine(url, echo=True)
```

または特定クエリの生成 SQL を確認：
```python
print(str(stmt.compile(compile_kwargs={"literal_binds": True})))
```

### 24-4. Docker ログ

```bash
docker compose logs -f backend      # フォロー
docker compose logs --tail=100 backend
docker compose exec backend bash    # 中に入る
```

### 24-5. Cloud Run ログ

```bash
gcloud run services logs read ai-shifts-backend --region=asia-northeast1 --limit=50
```

---

## 25. パフォーマンス最適化

### 25-1. バックエンド

- **N+1 排除**: §18 参照
- **インデックス**: よく `WHERE` に来るカラムに `index=True`
- **SELECT カラム指定**: 全カラム取得より `select(Employee.id, Employee.name)` の方が速い
- **ページング**: `LIMIT/OFFSET` は深いページで遅い → cursor pagination

### 25-2. フロントエンド

- **バンドルサイズ**: `npm run build` → chunk size 警告に注意
- **動的 import**: `defineAsyncComponent(() => import('./Heavy.vue'))`
- **v-memo**: 巨大リストの再描画を抑制
- **画像**: `<img loading="lazy">`

### 25-3. 計測

- FastAPI: middleware で `X-Process-Time` を出す
- フロント: DevTools の Performance タブ
- Lighthouse で総合スコア

### 25-4. Cloud Run のコールドスタート

- min-instances=1 にすると常時起動（料金増）
- 依存の少ないベースイメージ（alpine系）で起動時間短縮
- `startup CPU boost` を有効化

---

## 26. セキュリティのチェックポイント

### 26-1. 認証・認可

- 全 admin エンドポイントに `Depends(require_admin)` があるか？
- テスト: `admin 権限なしユーザーで叩いたら 403` を書く

### 26-2. 入力検証

- Pydantic の Field / validator を使い切る
- 数値範囲、文字列長、正規表現
- SQL Injection: SQLAlchemy 標準 API + バインドパラメータで防御

### 26-3. XSS

- Vue のテンプレート `{{ }}` は自動エスケープ → OK
- `v-html` を使うときは信頼された文字列のみ
- URL パラメータをそのまま埋め込まない

### 26-4. 秘密情報

- Secret Manager / 環境変数から読む
- ログに漏らさない（トークン全体を出さない、末尾数文字だけ）
- `.env` は commit しない（`.env.example` は OK）

### 26-5. CORS

- 本番の `FRONTEND_ORIGIN` を厳密指定
- `allow_origins=["*"]` は開発だけ

### 26-6. 依存性の脆弱性

- GitHub Dependabot alerts
- `npm audit`, `pip-audit`
- 定期的に依存を更新（chore(deps): の PR で）

---

## 27. CI / CD の仕組み

### 27-1. `.github/workflows/ci.yml`

現状の CI（コミット時 / PR 時に走る）：
1. **backend job**: Postgres サービスコンテナ起動 → `pip install` → `ruff check` → `pytest`
2. **frontend job**: `npm install` → `npm run build` → `npm run test:unit`

### 27-2. マージ前チェック

- CI green 必須（GitHub の branch protection で強制）
- レビュアー承認 1 名以上
- Conversation resolved

### 27-3. デプロイパイプライン（将来）

現状は手動 `docker build → push → gcloud run update`。自動化するなら：
```yaml
# .github/workflows/deploy.yml
on:
  push:
    branches: [main]
jobs:
  deploy:
    ...
```

Workload Identity Federation でサービスアカウントキー不要にするのが安全。

### 27-4. Pre-commit フック

`.pre-commit-config.yaml` により commit 時に：
- Ruff（Python lint/format）
- Prettier（フロント format）
- trailing whitespace 除去
- 大きなファイル警告
- YAML/JSON パース

有効化：
```bash
pip install pre-commit
pre-commit install
```

---

## 28. 機能追加のフルサイクル演習

「従業員に **入社日 (`hire_date`)** カラムを追加し、フロントで表示できるようにする」を例に、全工程を歩きます。

### 28-1. モデル修正

```python
# backend/app/models/employee.py
class Employee(Base):
    ...
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
```

### 28-2. マイグレーション生成 & 適用

```bash
cd backend
uv run alembic revision --autogenerate -m "add hire_date to employees"
# 生成された alembic/versions/xxxx.py を確認
uv run alembic upgrade head
```

### 28-3. Pydantic スキーマ更新

```python
# backend/app/schemas/employee.py
class EmployeeBase(BaseModel):
    ...
    hire_date: date | None = None
```

自動的に `EmployeeRead` / `EmployeeCreate` / `EmployeeUpdate` に反映。

### 28-4. ルーターは変更不要

Pydantic 経由で自動でシリアライズされる。

### 28-5. TypeScript 型追加

```ts
// frontend/src/types/index.ts
export interface Employee {
  ...
  hire_date: string | null   // ISO 日付
}
```

### 28-6. UI 追加

```vue
<!-- EmployeesView.vue のカラム定義 -->
{ title: '入社日', key: 'hire_date' },

<!-- 編集モーダルに追加 -->
<NFormItem label="入社日">
  <NDatePicker v-model:formatted-value="form.hire_date" value-format="yyyy-MM-dd" />
</NFormItem>
```

### 28-7. テスト追加

```python
# backend/tests/test_employees.py（新規）
def test_create_employee_with_hire_date(client, admin_token):
    r = client.post(
        "/api/employees",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "田中", "hire_date": "2024-04-01"},
    )
    assert r.status_code == 201
    assert r.json()["hire_date"] == "2024-04-01"
```

### 28-8. 動作確認

```bash
# バックエンド起動
cd backend && uv run uvicorn app.main:app --reload

# フロントエンド起動（別ターミナル）
cd frontend && npm run dev

# ブラウザ確認
# → 従業員管理画面で新規作成時に入社日入力できる
# → 一覧に入社日カラム表示
```

### 28-9. コミット + PR

```bash
git checkout -b feat/employee-hire-date
git add backend/app/models/employee.py backend/app/schemas/employee.py \
        backend/alembic/versions/xxxx_add_hire_date.py \
        backend/tests/test_employees.py \
        frontend/src/types/index.ts frontend/src/views/EmployeesView.vue
git commit -m "feat(employee): 入社日フィールドを追加"
git push -u origin feat/employee-hire-date
gh pr create --title "feat(employee): 入社日フィールドを追加" --body "..."
```

**この一連の流れが自然にできれば、あなたは中級者です 🎉**

---

## 参考リンク

- **Vue 3 公式**: https://ja.vuejs.org/
- **FastAPI 公式**: https://fastapi.tiangolo.com/ja/
- **Pydantic 公式**: https://docs.pydantic.dev/
- **SQLAlchemy 2.0 tutorial**: https://docs.sqlalchemy.org/en/20/tutorial/
- **OR-tools CP-SAT**: https://developers.google.com/optimization/cp/cp_solver
- **Naive UI**: https://www.naiveui.com/
- **Anthropic API docs**: https://docs.anthropic.com/
- **Supabase docs**: https://supabase.com/docs
- **Terraform (Google)**: https://registry.terraform.io/providers/hashicorp/google/latest/docs

わからないことがあったら、Slack / Discord などのチームチャットで気軽に聞いてください。「初歩的すぎる質問」なんてありません。
