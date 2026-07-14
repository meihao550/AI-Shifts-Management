# チュートリアル — 初心者向けガイド

このドキュメントは、**プログラミング初心者** の方が AI-Shifts-Management プロジェクトを触れるようになることを目的にしています。

- 対象読者：Web アプリを触ったことはあるが、Vue / FastAPI などは初めて
- ゴール：ローカルで動かせる → コードを読み書きできる → PR を出せる
- 所要時間：初回セットアップ 30 分 + 各章 15〜30 分

---

## 目次

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
14. [次のステップ](#14-次のステップ)

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

## 14. 次のステップ

この後どこから触り始めるか、レベル別のオススメ：

### ★☆☆ とりあえずコードに触ってみたい
- `frontend/src/views/DashboardView.vue` の見た目を少し変えてみる
- `backend/tests/test_payroll.py` を実行して、新しいテストケースを追加
- Naive UI のドキュメントを見ながら新しい部品を試す

### ★★☆ 機能追加してみたい
- ダッシュボードに「今月の勤務トップ 3」表示を追加
  - backend にエンドポイント追加 → schema/router 拡張 → frontend で表示
- 従業員に「入社日」フィールドを追加
  - モデル → マイグレーション → スキーマ → API → 画面

### ★★★ アーキテクチャを触りたい
- CP-SAT のソフト制約に「連勤 3 日以内」を追加
- LLM プロンプトを日本語 → 英語版にして精度比較
- Terraform に staging 環境を追加

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
