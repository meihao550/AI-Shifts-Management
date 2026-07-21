# ハンズオン: シフト管理アプリをゼロから作る

このチュートリアルは、**何もない状態から手を動かして**、このリポジトリと同じ「シフト管理アプリ」のコア機能を作り上げるためのものです。読むだけでなく、**実際にコードを打ち込みながら**進めてください。

## このチュートリアルのゴール

最終的に、ブラウザから使える次の機能を**自分で作れる**ようになります。

- 従業員の追加・編集・削除（CRUD）
- 希望日／勤務不可日をカレンダーでクリック登録
- シフトパターン・必要人数のルール設定
- **CP-SAT による 1 か月分のシフト自動生成**
- 生成結果の表示、日本の祝日表示

> 認証（Googleログイン）・給与計算・PDF/Excel 出力・LLM 連携は、コアが完成した後の [第10章 拡張課題](#第10章-拡張課題本物に近づける) で、本物のソースコードへ誘導します。まずは動くものを最短で作り、全体像を体で覚えるのが狙いです。

## 対象読者と進め方

- **想定**: プログラミングは少し触ったことがあるが、Vue / FastAPI は初めて〜駆け出し。
- **前提ソフト**: Python 3.11 以上 / Node.js 20 以上 / 好きなエディタ（VS Code 推奨）/ ターミナル。
- **所要時間**: 全10章で 4〜8 時間ほど。1 章ずつ「動作確認」まで終えてから次へ。
- **詰まったら**: 各章末の「うまくいかないとき」を見てください。

> 📌 **本物との違い**: 学習しやすさ優先で、DB は **SQLite**（設定不要）を使い、認証は省略します。本物は PostgreSQL + Alembic + Google OAuth です。第10章でその差を埋めます。既存プロジェクトの該当コードは随時リンクします。

---

## 目次

- [第0章 全体像とプロジェクト作成](#第0章-全体像とプロジェクト作成)
- [第1章 バックエンドの土台（FastAPI）](#第1章-バックエンドの土台fastapi)
- [第2章 データベースとモデル（SQLAlchemy）](#第2章-データベースとモデルsqlalchemy)
- [第3章 従業員 CRUD API](#第3章-従業員-crud-api)
- [第4章 フロントの土台（Vue + Vite）](#第4章-フロントの土台vue--vite)
- [第5章 従業員管理画面](#第5章-従業員管理画面)
- [第6章 希望カレンダー](#第6章-希望カレンダー)
- [第7章 ルール設定（パターン・必要人数）](#第7章-ルール設定パターン必要人数)
- [第8章 シフト自動生成（CP-SAT）](#第8章-シフト自動生成cp-sat)
- [第9章 祝日表示と仕上げ](#第9章-祝日表示と仕上げ)
- [第10章 拡張課題（本物に近づける）](#第10章-拡張課題本物に近づける)

---

## 第0章 全体像とプロジェクト作成

### 作るものの構造

```
ブラウザ  ⇄  フロントエンド (Vue)  ⇄  バックエンド (FastAPI)  ⇄  DB (SQLite)
             画面・操作              API・計算(CP-SAT)          データ保存
```

- **フロント**（`frontend/`）: 画面。Vue 3 + TypeScript + Vite + naive-ui。
- **バック**（`backend/`）: API サーバ。FastAPI + SQLAlchemy + OR-Tools。
- 両者は **JSON を HTTP でやり取り**します（これが API）。

### プロジェクトフォルダを作る

```bash
mkdir myshifts && cd myshifts
mkdir backend frontend
```

以降、`myshifts/` を作業ルートとします。バックエンドとフロントエンドは別々のターミナルで動かします。

---

## 第1章 バックエンドの土台（FastAPI）

**目標**: `GET /api/health` にアクセスすると `{"status":"ok"}` が返るサーバを立てる。

### 1-1. 仮想環境とインストール

`backend/` の中で作業します。**仮想環境**は「このプロジェクト専用のライブラリ置き場」です。

```bash
cd backend
python -m venv .venv                 # .venv フォルダに仮想環境を作成
source .venv/bin/activate            # 有効化（Windows: .venv\Scripts\activate）
pip install "fastapi[standard]" sqlalchemy
```

> `[standard]` を付けると開発サーバ `uvicorn` なども一緒に入ります。

### 1-2. 最初のエンドポイント

`backend/app/__init__.py`（空ファイル）と `backend/app/main.py` を作ります。

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MyShifts API")

# フロント(localhost:5173)からのアクセスを許可（第4章で使う）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

### 1-3. 起動して確認

```bash
uvicorn app.main:app --reload --port 8000
```

ブラウザで次を開きます。

- <http://localhost:8000/api/health> → `{"status":"ok"}` が出れば成功。
- <http://localhost:8000/docs> → **API を試せる画面**（FastAPI が自動生成）。これから作る API がここに全部並びます。

> 🔑 **解説**: `@app.get("/api/health")` の `@` は**デコレータ**で、「この URL に GET が来たら下の関数を実行」という登録です。`--reload` はコードを保存するたび自動で再起動してくれる開発用オプション。

### うまくいかないとき
- `command not found: uvicorn` → 仮想環境を有効化し忘れ。`source .venv/bin/activate` を再実行。
- ポート使用中 → `--port 8001` など別番号に。

---

## 第2章 データベースとモデル（SQLAlchemy）

**目標**: SQLite に接続し、`employees` テーブルを Python のクラスで定義する。

### 2-1. DB 接続の準備

`backend/app/database.py`:

```python
# backend/app/database.py
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# SQLite ファイル myshifts.db に保存（設定不要でお手軽）
engine = create_engine("sqlite:///./myshifts.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """全モデルの親クラス"""


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db          # リクエスト中だけ使い、
    finally:
        db.close()        # 終わったら必ず閉じる
```

- **engine**: DB への回線。SQLite はただのファイル 1 個。
- **Session**: DB とのやり取り 1 回分の「作業台」。
- **Base**: これから作るモデルの共通の親。
- **get_db**: リクエストごとにセッションを配る関数（第3章で使う）。

> 📎 本物は PostgreSQL に接続します（[`backend/app/core/database.py`](../backend/app/core/database.py)）。違いは接続文字列だけで、構造は同じです。

### 2-2. 従業員モデル

`backend/app/models.py`（本物は種類ごとにファイル分割していますが、学習用に 1 ファイルにまとめます）:

```python
# backend/app/models.py
from __future__ import annotations
from datetime import date
from enum import StrEnum
from sqlalchemy import Boolean, Date, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    hourly_wage: Mapped[int] = mapped_column(Integer, default=1100, nullable=False)
    main_shift_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    weekly_shifts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    availabilities: Mapped[list[Availability]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )


class AvailabilityKind(StrEnum):
    unavailable = "unavailable"   # 絶対勤務不可
    preferred = "preferred"       # 入りたい


class Availability(Base):
    __tablename__ = "availabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    kind: Mapped[AvailabilityKind] = mapped_column(SAEnum(AvailabilityKind, name="kind"))

    employee: Mapped[Employee] = relationship(back_populates="availabilities")
```

読みどころ:
- `mapped_column(..., primary_key=True)` = 主キー（1 件ごとの番号）。
- `nullable=False` = 必須、`default=1100` = 初期値。
- `relationship(...)` = テーブル同士の関係（従業員 1 人 ⇄ 希望 複数）。

### 2-3. テーブルを実際に作る

`backend/app/main.py` の先頭付近に、起動時テーブル作成を追加します。

```python
# backend/app/main.py （追記）
from app.database import Base, engine
from app import models  # noqa: F401  ← モデルを読み込ませる（テーブル登録のため）

Base.metadata.create_all(bind=engine)   # 無ければテーブルを作成
```

サーバを再起動すると `backend/myshifts.db` が生成されます。

> 📎 本物は起動時 `create_all` ではなく **Alembic マイグレーション**でテーブルを管理します（第10章）。学習中は `create_all` が手軽です。

---

## 第3章 従業員 CRUD API

**目標**: 従業員を「一覧・作成・更新・削除」できる API を作る。

### 3-1. 入出力の形（Pydantic スキーマ）

DB モデルとは別に、**API でやり取りするデータの形**を定義します。`backend/app/schemas.py`:

```python
# backend/app/schemas.py
from datetime import date
from pydantic import BaseModel, ConfigDict, Field
from app.models import AvailabilityKind


class EmployeeBase(BaseModel):
    name: str
    hourly_wage: int = Field(default=1100, ge=0)       # 0 以上
    main_shift_type: str | None = None
    weekly_shifts: int = Field(default=3, ge=0, le=7)  # 0〜7
    active: bool = True


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):                        # 更新は全項目 任意
    name: str | None = None
    hourly_wage: int | None = Field(default=None, ge=0)
    main_shift_type: str | None = None
    weekly_shifts: int | None = Field(default=None, ge=0, le=7)
    active: bool | None = None


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)    # DBオブジェクトから変換OK
    id: int


class AvailabilityCreate(BaseModel):
    employee_id: int
    target_date: date
    shift_type: str | None = None
    kind: AvailabilityKind


class AvailabilityRead(AvailabilityCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
```

> 🔑 **なぜ models と分ける？** DB の生データをそのまま外に出すと危険＆不便だから。`Field(ge=0)` のような**入力検査**もここで自動化されます（負の時給を送ると自動で 422 エラー）。

### 3-2. 従業員ルーター

`backend/app/routers/__init__.py`（空）と `backend/app/routers/employees.py`:

```python
# backend/app/routers/employees.py
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Employee
from app import schemas

router = APIRouter(prefix="/employees", tags=["employees"])
DB = Annotated[Session, Depends(get_db)]   # 「DBセッションを注入」の短縮形


@router.get("", response_model=list[schemas.EmployeeRead])
def list_employees(db: DB):
    return list(db.execute(select(Employee).order_by(Employee.id)).scalars())


@router.post("", response_model=schemas.EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(payload: schemas.EmployeeCreate, db: DB):
    emp = Employee(**payload.model_dump())
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


@router.patch("/{employee_id}", response_model=schemas.EmployeeRead)
def update_employee(employee_id: int, payload: schemas.EmployeeUpdate, db: DB):
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(404, "employee not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(emp, key, value)
    db.commit()
    db.refresh(emp)
    return emp


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(employee_id: int, db: DB):
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(404, "employee not found")
    db.delete(emp)
    db.commit()
```

### 3-3. ルーターを main に登録

```python
# backend/app/main.py （追記）
from app.routers import employees

app.include_router(employees.router, prefix="/api")
```

### 3-4. 動作確認

<http://localhost:8000/docs> を開き、`POST /api/employees` の「Try it out」で

```json
{ "name": "田中太郎", "hourly_wage": 1200, "weekly_shifts": 4 }
```

を送信 → 201 と `id` 付きの応答が返ればOK。`GET /api/employees` で一覧に出ます。

> 🔑 **CRUD と HTTP メソッド**: 一覧/取得=GET、作成=POST、一部更新=PATCH、削除=DELETE。この対応は Web API の共通ルールです。本物の [`routers/employees.py`](../backend/app/routers/employees.py) もこれに `_admin: AdminUser`（管理者チェック）が付くだけで骨格は同じです。

---

## 第4章 フロントの土台（Vue + Vite）

**目標**: Vue アプリを立ち上げ、バックエンドの `/api/health` を画面から呼ぶ。

### 4-1. プロジェクト作成

別ターミナルを開き、`myshifts/` で:

```bash
cd frontend
npm create vite@latest . -- --template vue-ts    # カレントに Vue+TS 雛形を作成
npm install
npm install axios pinia vue-router naive-ui
```

`npm run dev` で <http://localhost:5173> が開けば雛形は動いています。

### 4-2. API クライアント

`frontend/src/api/client.ts`:

```ts
// frontend/src/api/client.ts
import axios from 'axios'

export const api = axios.create({
  baseURL: 'http://localhost:8000/api',   // バックエンドの入口
  timeout: 30000,
})
```

> `baseURL` に `/api` まで入れておくと、以降は `api.get('/employees')` のように短く書けます。

### 4-3. ルーター・Pinia・naive-ui を有効化

`frontend/src/main.ts` を次の内容に:

```ts
// frontend/src/main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import naive from 'naive-ui'
import App from './App.vue'
import router from './router'

createApp(App).use(createPinia()).use(router).use(naive).mount('#app')
```

- **Pinia** = 画面をまたいでデータを共有する「状態の入れ物」。
- **vue-router** = URL と画面（View）の対応付け。
- **naive-ui** = ボタンや表などの UI 部品集。

`frontend/src/router/index.ts`:

```ts
// frontend/src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/employees' },
    { path: '/employees', component: () => import('@/views/EmployeesView.vue') },
    { path: '/shift', component: () => import('@/views/ShiftTableView.vue') },
    { path: '/rules', component: () => import('@/views/RulesView.vue') },
  ],
})
```

> `@/` は `src/` を指す別名です。Vite の設定に無ければ、`frontend/vite.config.ts` の `defineConfig({...})` に以下を足します。
> ```ts
> import { fileURLToPath, URL } from 'node:url'
> // resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } }
> ```

`frontend/src/App.vue` を最小の骨組みに:

```vue
<!-- frontend/src/App.vue -->
<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { NMessageProvider } from 'naive-ui'
</script>

<template>
  <NMessageProvider>
    <nav style="display:flex; gap:16px; padding:12px; background:#f2f4f9">
      <RouterLink to="/employees">従業員</RouterLink>
      <RouterLink to="/rules">ルール</RouterLink>
      <RouterLink to="/shift">シフト表</RouterLink>
    </nav>
    <main style="max-width:1100px; margin:0 auto; padding:24px">
      <RouterView />
    </main>
  </NMessageProvider>
</template>
```

> 🔑 **View と component**: `RouterView` の場所に、URL に応じた画面（`views/*.vue`）が差し込まれます。`RouterLink` は画面遷移リンク。

---

## 第5章 従業員管理画面

**目標**: 従業員を一覧・追加・削除できる画面を作る。

### 5-1. 型定義

`frontend/src/types.ts`:

```ts
// frontend/src/types.ts
export interface Employee {
  id: number
  name: string
  hourly_wage: number
  main_shift_type: string | null
  weekly_shifts: number
  active: boolean
}
```

### 5-2. Pinia ストア

`frontend/src/stores/employee.ts`:

```ts
// frontend/src/stores/employee.ts
import { defineStore } from 'pinia'
import { api } from '@/api/client'
import type { Employee } from '@/types'

export const useEmployeeStore = defineStore('employee', {
  state: () => ({ employees: [] as Employee[] }),
  actions: {
    async fetchAll() {
      const { data } = await api.get<Employee[]>('/employees')
      this.employees = data
    },
    async create(payload: Partial<Employee>) {
      const { data } = await api.post<Employee>('/employees', payload)
      this.employees.push(data)
    },
    async remove(id: number) {
      await api.delete(`/employees/${id}`)
      this.employees = this.employees.filter((e) => e.id !== id)
    },
  },
})
```

> 🔑 **ストアの役割**: 「サーバから取ってきた従業員リスト」を画面全体で共有し、追加・削除でその場更新します。本物の [`stores/employee.ts`](../frontend/src/stores/employee.ts) とほぼ同じ形です。

### 5-3. 画面（View）

`frontend/src/views/EmployeesView.vue`:

```vue
<!-- frontend/src/views/EmployeesView.vue -->
<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import { NButton, NDataTable, NInput, NInputNumber, NSpace, useMessage } from 'naive-ui'
import { useEmployeeStore } from '@/stores/employee'

const store = useEmployeeStore()
const message = useMessage()
const name = ref('')
const wage = ref(1100)
const weekly = ref(3)

onMounted(() => store.fetchAll())

async function add() {
  if (!name.value) return message.warning('名前を入力してください')
  await store.create({ name: name.value, hourly_wage: wage.value, weekly_shifts: weekly.value })
  name.value = ''
  message.success('追加しました')
}

const columns = [
  { title: 'ID', key: 'id' },
  { title: '名前', key: 'name' },
  { title: '時給', key: 'hourly_wage' },
  { title: '週回数', key: 'weekly_shifts' },
  {
    title: '操作',
    key: 'actions',
    render(row: { id: number }) {
      return h(
        NButton,
        { size: 'small', type: 'error', onClick: () => store.remove(row.id) },
        () => '削除',
      )
    },
  },
]
</script>

<template>
  <h2>従業員管理</h2>
  <NSpace align="center" style="margin-bottom:16px">
    <NInput v-model:value="name" placeholder="名前" style="width:160px" />
    <NInputNumber v-model:value="wage" :min="0" />
    <NInputNumber v-model:value="weekly" :min="0" :max="7" />
    <NButton type="primary" @click="add">追加</NButton>
  </NSpace>
  <NDataTable :columns="columns" :data="store.employees" :row-key="(r) => r.id" />
</template>
```

> `render` 内で使う `h` は「要素を作る関数」です（`import { h } from 'vue'`）。naive-ui の表でボタンなど部品を差し込むときに使います。

### 5-4. 動作確認

`/employees` を開き、名前を入れて「追加」→ 表に増える。「削除」→ 消える。バックエンドの `GET /api/employees` にも反映されていれば、**フロントとバックがつながった**証拠です。🎉

> 🔑 **データの流れ**: 画面のボタン → ストアの action → `api.post` → FastAPI → DB。第0章の図が実感できたはずです。

---

## 第6章 希望カレンダー

**目標**: 従業員を選び、カレンダーの日付を**クリックで「休日→希望日→解除」と循環**登録する。
（これはこのリポジトリで実際に実装されている挙動です。）

### 6-1. バックエンド: availability API

`backend/app/routers/employees.py` に追記します。

```python
# backend/app/routers/employees.py （追記）
from app.models import Availability

@router.get("/{employee_id}/availabilities", response_model=list[schemas.AvailabilityRead])
def list_availabilities(employee_id: int, db: DB):
    stmt = select(Availability).where(Availability.employee_id == employee_id)
    return list(db.execute(stmt).scalars())


@router.post("/availabilities", response_model=schemas.AvailabilityRead, status_code=201)
def create_availability(payload: schemas.AvailabilityCreate, db: DB):
    row = Availability(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/availabilities/{availability_id}", status_code=204)
def delete_availability(availability_id: int, db: DB):
    row = db.get(Availability, availability_id)
    if not row:
        raise HTTPException(404, "not found")
    db.delete(row)
    db.commit()
```

### 6-2. フロント: ストアに希望操作を追加

`frontend/src/types.ts` に追記:

```ts
export type AvailabilityKind = 'unavailable' | 'preferred'
export interface Availability {
  id: number
  employee_id: number
  target_date: string
  shift_type: string | null
  kind: AvailabilityKind
}
```

`stores/employee.ts` の `actions` に追記:

```ts
async listAvailabilities(id: number) {
  const { data } = await api.get<Availability[]>(`/employees/${id}/availabilities`)
  return data
},
async createAvailability(payload: Omit<Availability, 'id'>) {
  const { data } = await api.post<Availability>('/employees/availabilities', payload)
  return data
},
async deleteAvailability(id: number) {
  await api.delete(`/employees/availabilities/${id}`)
},
```

（`Availability` の import も忘れずに。）

### 6-3. カレンダーコンポーネント

`frontend/src/components/AvailabilityCalendar.vue`。**クリックで状態を循環**させ、素早い連打でも順序が崩れないよう日付ごとに直列処理します。

```vue
<!-- frontend/src/components/AvailabilityCalendar.vue -->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { NSelect, NSpace, useMessage } from 'naive-ui'
import { useEmployeeStore } from '@/stores/employee'
import type { Availability, AvailabilityKind } from '@/types'

const props = defineProps<{ year: number; month: number }>()
const store = useEmployeeStore()
const message = useMessage()
const selected = ref<number | null>(null)
const items = ref<Availability[]>([])

const options = computed(() => store.employees.map((e) => ({ label: e.name, value: e.id })))
const days = computed(() => {
  const n = new Date(props.year, props.month, 0).getDate()
  return Array.from({ length: n }, (_, i) => new Date(props.year, props.month - 1, i + 1))
})

function iso(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function on(d: Date) {
  return items.value.filter((a) => a.target_date === iso(d))
}

async function refresh() {
  if (!selected.value) return (items.value = [])
  const rows = await store.listAvailabilities(selected.value)
  items.value = rows.filter((r) => r.target_date.startsWith(`${props.year}-${String(props.month).padStart(2, '0')}`))
}
watch(selected, refresh)
onMounted(async () => {
  if (!store.employees.length) await store.fetchAll()
  selected.value = store.employees[0]?.id ?? null
})

async function add(kind: AvailabilityKind, d: Date) {
  const created = await store.createAvailability({
    employee_id: selected.value!, target_date: iso(d), kind, shift_type: null,
  })
  items.value.push(created)
}
async function remove(id: number) {
  await store.deleteAvailability(id)
  items.value = items.value.filter((a) => a.id !== id)
}

// クリックで循環: なし → 休日 → 希望日 → なし。連打対策で日付ごとに直列化。
const chains = new Map<string, Promise<void>>()
function cycle(d: Date) {
  if (!selected.value) return
  const key = iso(d)
  const prev = chains.get(key) ?? Promise.resolve()
  chains.set(key, prev.then(() => step(d)).catch((e) => message.error(String(e))))
}
async function step(d: Date) {
  const cur = on(d)
  const un = cur.find((i) => i.kind === 'unavailable')
  const pref = cur.find((i) => i.kind === 'preferred')
  if (!un && !pref) await add('unavailable', d)
  else if (un && !pref) { await remove(un.id); await add('preferred', d) }
  else if (pref && !un) await remove(pref.id)
  else for (const it of cur) await remove(it.id)
}

function cls(d: Date) {
  const c = on(d)
  if (c.some((i) => i.kind === 'unavailable')) return 'day un'
  if (c.some((i) => i.kind === 'preferred')) return 'day pref'
  return 'day'
}
</script>

<template>
  <NSpace align="center" style="margin-bottom:12px">
    <span>従業員:</span>
    <NSelect v-model:value="selected" :options="options" style="width:200px" />
    <span style="color:#888">クリック: 1回=休日 / 2回=希望 / 3回=解除</span>
  </NSpace>
  <div class="cal">
    <div v-for="w in ['日','月','火','水','木','金','土']" :key="w" class="head">{{ w }}</div>
    <div v-for="i in days[0].getDay()" :key="'p'+i" />
    <div v-for="d in days" :key="d.getTime()" :class="cls(d)" @click="cycle(d)">
      {{ d.getDate() }}
    </div>
  </div>
</template>

<style scoped>
.cal { display:grid; grid-template-columns:repeat(7,1fr); gap:4px }
.head { text-align:center; font-weight:600; padding:6px 0; background:#f2f4f9; border-radius:6px }
.day { min-height:52px; padding:4px; border:1px solid #dde1e8; border-radius:6px; cursor:pointer; user-select:none }
.day.un { background:#fdecec; border-color:#f5c2c2 }
.day.pref { background:#e8f7ec; border-color:#bde0c6 }
</style>
```

### 6-4. シフト表画面に置く

`frontend/src/views/ShiftTableView.vue`（この章では暫定。第8章で拡張）:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import AvailabilityCalendar from '@/components/AvailabilityCalendar.vue'
const year = ref(2026), month = ref(7)
</script>
<template>
  <h2>{{ year }}年{{ month }}月</h2>
  <AvailabilityCalendar :year="year" :month="month" />
</template>
```

`/shift` を開き、従業員を選んで日付をクリック → 赤（休日）→ 緑（希望）→ 白（解除）と循環すれば成功。DB の `availabilities` にも記録されます。

> 🔑 **なぜ直列化？** クリックのたびに非同期 API を呼ぶので、素早い 2 連打で 1 回目完了前に 2 回目が走ると状態が壊れます。`chains` に前回の Promise を覚えておき「前が終わってから次」を保証しています。

---

## 第7章 ルール設定（パターン・必要人数）

**目標**: シフトの型（朝/夜/深夜）と、必要人数（平日/週末で何人）を DB に持たせる。第8章の入力になります。

### 7-1. モデル追加

`backend/app/models.py` に追記:

```python
from datetime import time
from sqlalchemy import Time

class DayCategory(StrEnum):
    weekday = "weekday"
    weekend_or_holiday = "weekend_or_holiday"

class ShiftPattern(Base):
    __tablename__ = "shift_patterns"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)   # morning/evening/night
    label: Mapped[str] = mapped_column(String(64))
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    is_basic: Mapped[bool] = mapped_column(Boolean, default=True)
    category: Mapped[str] = mapped_column(String(16))            # morning/evening/night

class StaffingRule(Base):
    __tablename__ = "staffing_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day_category: Mapped[DayCategory] = mapped_column(SAEnum(DayCategory, name="day_cat"))
    shift_category: Mapped[str] = mapped_column(String(16))
    required: Mapped[int] = mapped_column(Integer)
```

`myshifts.db` を一度削除して再起動すると、新テーブルが作られます（学習用の割り切り。本物は Alembic で差分適用）。

### 7-2. 既定データを自動投入 + 取得 API

`backend/app/routers/rules.py`:

```python
# backend/app/routers/rules.py
from datetime import time
from fastapi import APIRouter
from sqlalchemy import select
from app.database import get_db
from app.models import DayCategory, ShiftPattern, StaffingRule
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/rules", tags=["rules"])
DB = Annotated[Session, Depends(get_db)]

DEFAULT_PATTERNS = [
    ("morning", "朝 09-17", time(9, 0), time(17, 0), "morning"),
    ("evening", "夜 17-01", time(17, 0), time(1, 0), "evening"),
    ("night", "深夜 01-09", time(1, 0), time(9, 0), "night"),
]
DEFAULT_STAFFING = [
    ("weekday", "morning", 2), ("weekday", "evening", 2), ("weekday", "night", 1),
    ("weekend_or_holiday", "morning", 3), ("weekend_or_holiday", "evening", 3),
    ("weekend_or_holiday", "night", 1),
]


def ensure_defaults(db: Session):
    if not db.execute(select(ShiftPattern)).first():
        db.add_all([ShiftPattern(code=c, label=l, start_time=s, end_time=e,
                                 is_basic=True, category=cat) for c, l, s, e, cat in DEFAULT_PATTERNS])
    if not db.execute(select(StaffingRule)).first():
        db.add_all([StaffingRule(day_category=DayCategory(dc), shift_category=sc, required=r)
                    for dc, sc, r in DEFAULT_STAFFING])
    db.commit()


@router.get("/patterns")
def list_patterns(db: DB):
    ensure_defaults(db)
    return list(db.execute(select(ShiftPattern)).scalars())


@router.get("/staffing")
def list_staffing(db: DB):
    ensure_defaults(db)
    return [{"day_category": r.day_category.value, "shift_category": r.shift_category,
             "required": r.required} for r in db.execute(select(StaffingRule)).scalars()]
```

`main.py` に `app.include_router(rules.router, prefix="/api")` を追加。

`GET /api/rules/patterns` を叩くと、初回に既定 3 パターンが投入されて返ります。

> 📎 本物はこれを画面から編集できます（[`routers/rules.py`](../backend/app/routers/rules.py) / [`RulesView.vue`](../frontend/src/views/RulesView.vue)）。ここでは自動投入だけで先へ進みます。

---

## 第8章 シフト自動生成（CP-SAT）

いよいよ**心臓部**です。「必要人数を満たしつつ、希望や得意シフトをできるだけ叶える」最適な割り当てを OR-Tools で解きます。

### 8-1. インストールと祝日判定

```bash
pip install ortools jpholiday
```

`backend/app/services/__init__.py`（空）と `backend/app/services/holidays.py`:

```python
# backend/app/services/holidays.py
from datetime import date
import jpholiday

def category_for(d: date) -> str:
    is_holiday = d.weekday() >= 5 or bool(jpholiday.is_holiday(d))
    return "weekend_or_holiday" if is_holiday else "weekday"
```

### 8-2. スケジューラ本体

`backend/app/services/scheduler.py`。まず「考え方」を掴んでからコードへ。

- **決定変数** `x[e,d,p]`: 従業員 e を 日 d の パターン p に入れる？（1=はい / 0=いいえ）
- **ハード制約（絶対）**: ①1人1日1パターン ②勤務不可日は入れない ③必要人数ちょうど
- **目的関数（なるべく）**: 週目標との差を小さく／希望日・得意シフトはご褒美

```python
# backend/app/services/scheduler.py
from __future__ import annotations
import calendar
from dataclasses import dataclass
from datetime import date, time
from ortools.sat.python import cp_model
from app.services.holidays import category_for


@dataclass(frozen=True)
class Pattern:
    id: int; code: str; start: time; end: time; category: str

@dataclass(frozen=True)
class Emp:
    id: int; name: str; weekly_target: int; main_shift_type: str | None

@dataclass
class Avail:
    employee_id: int; target_date: date; kind: str; shift_type: str | None = None


def solve(year, month, emps: list[Emp], pats: list[Pattern],
          staffing: dict[tuple[str, str], int], avails: list[Avail]) -> dict:
    model = cp_model.CpModel()
    _, ndays = calendar.monthrange(year, month)
    days = [date(year, month, d) for d in range(1, ndays + 1)]

    unavailable = {(a.employee_id, a.target_date) for a in avails if a.kind == "unavailable"}
    preferred = {(a.employee_id, a.target_date) for a in avails if a.kind == "preferred"}

    # 決定変数 x[e,d,p]
    x = {}
    for e in emps:
        for d in days:
            for p in pats:
                x[(e.id, d, p.id)] = model.NewBoolVar(f"x_{e.id}_{d}_{p.code}")

    # H1: 1人1日1パターンまで
    for e in emps:
        for d in days:
            model.Add(sum(x[(e.id, d, p.id)] for p in pats) <= 1)

    # H2: 勤務不可日は入れない
    for e in emps:
        for d in days:
            if (e.id, d) in unavailable:
                for p in pats:
                    model.Add(x[(e.id, d, p.id)] == 0)

    # H3: 必要人数ちょうど
    warnings = []
    for d in days:
        cat = category_for(d)
        for sc in ("morning", "evening", "night"):
            need = staffing.get((cat, sc), 0)
            in_cat = [p for p in pats if p.category == sc]
            if not in_cat:
                if need > 0:
                    warnings.append(f"{d}: {sc} のパターンが無く必要数を満たせません")
                continue
            model.Add(sum(x[(e.id, d, p.id)] for e in emps for p in in_cat) == need)

    # S1: 週目標との乖離ペナルティ
    penalties = []
    weeks = len(days) // 7 + (1 if len(days) % 7 else 0)
    for e in emps:
        target = max(0, e.weekly_target * weeks)
        total = sum(x[(e.id, d, p.id)] for d in days for p in pats)
        over = model.NewIntVar(0, len(days), f"over_{e.id}")
        under = model.NewIntVar(0, len(days), f"under_{e.id}")
        model.Add(total - target == over - under)
        penalties += [over, under]

    # S2: 希望日ボーナス
    bonus = [x[(eid, d, p.id)] for (eid, d) in preferred for p in pats if (eid, d, p.id) in x]

    # S3: 得意シフトボーナス
    main_bonus = [x[(e.id, d, p.id)] for e in emps if e.main_shift_type
                  for d in days for p in pats
                  if p.code == e.main_shift_type or p.category == e.main_shift_type]

    # 目的関数: ペナルティは小さく、ボーナスは引いて報酬に。重み 5 > 3 > 1。
    obj = sum(penalties) - 3 * sum(bonus) - 5 * sum(main_bonus)
    model.Minimize(obj)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 20
    status = solver.Solve(model)

    assignments = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for e in emps:
            for d in days:
                for p in pats:
                    if solver.Value(x[(e.id, d, p.id)]) == 1:
                        assignments.append({
                            "employee_id": e.id, "target_date": d.isoformat(),
                            "shift_type": p.code,
                        })
    else:
        warnings.append(f"解が見つかりませんでした ({solver.StatusName(status)})")
    return {"assignments": assignments, "status": solver.StatusName(status), "warnings": warnings}
```

> 🔑 **絶対偏差の線形化** (S1): `|total - target|` は最適化ソルバがそのまま扱えないので、`total - target = over - under`（over,under≥0）と分解し、`over + under` を最小化します。定番テクニックです。
>
> 🔑 **ボーナスを「引く」理由**: 目的は最小化なので、望ましい割り当てを引き算すると「入れたほうが値が下がる＝得」になり、優先されます。重み 5>3>1 で「得意シフト＞希望日＞労働量の均し」の順に効きます。

### 8-3. 生成エンドポイント

`backend/app/routers/shifts.py`:

```python
# backend/app/routers/shifts.py
from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Employee, ShiftPattern, StaffingRule, Availability
from app.services.scheduler import Emp, Pattern, Avail, solve

router = APIRouter(prefix="/shifts", tags=["shifts"])
DB = Annotated[Session, Depends(get_db)]

class GenerateRequest(BaseModel):
    year: int
    month: int

@router.post("/generate")
def generate(payload: GenerateRequest, db: DB):
    employees = list(db.execute(select(Employee).where(Employee.active.is_(True))).scalars())
    patterns = [p for p in db.execute(select(ShiftPattern)).scalars() if p.is_basic]
    staffing = {(r.day_category.value, r.shift_category): r.required
                for r in db.execute(select(StaffingRule)).scalars()}
    avails = list(db.execute(select(Availability)).scalars())

    result = solve(
        payload.year, payload.month,
        [Emp(e.id, e.name, e.weekly_shifts, e.main_shift_type) for e in employees],
        [Pattern(p.id, p.code, p.start_time, p.end_time, p.category) for p in patterns],
        staffing,
        [Avail(a.employee_id, a.target_date, a.kind.value, a.shift_type) for a in avails],
    )
    return result
```

`main.py` に `app.include_router(shifts.router, prefix="/api")` を追加。

> ⚠️ 生成前に「従業員数 ≥ 1日の最大必要人数」であることを確認してください（例: 平日 5 名・週末 7 名必要なら最低 7 名）。足りないと `INFEASIBLE`（解なし）になります。本物は事前チェックで親切なエラーを返します（[`routers/shifts.py`](../backend/app/routers/shifts.py)）。

### 8-4. フロントから生成して表示

`stores/shift.ts`:

```ts
// frontend/src/stores/shift.ts
import { defineStore } from 'pinia'
import { api } from '@/api/client'

interface Assignment { employee_id: number; target_date: string; shift_type: string }
interface Result { assignments: Assignment[]; status: string; warnings: string[] }

export const useShiftStore = defineStore('shift', {
  state: () => ({ result: null as Result | null, generating: false }),
  actions: {
    async generate(year: number, month: number) {
      this.generating = true
      try {
        const { data } = await api.post<Result>('/shifts/generate', { year, month })
        this.result = data
      } finally {
        this.generating = false
      }
    },
  },
})
```

`views/ShiftTableView.vue` を拡張:

```vue
<script setup lang="ts">
import { computed, ref } from 'vue'
import { NButton, useMessage } from 'naive-ui'
import AvailabilityCalendar from '@/components/AvailabilityCalendar.vue'
import { useEmployeeStore } from '@/stores/employee'
import { useShiftStore } from '@/stores/shift'

const year = ref(2026), month = ref(7)
const emp = useEmployeeStore()
const shift = useShiftStore()
const message = useMessage()

const nameOf = (id: number) => emp.employees.find((e) => e.id === id)?.name ?? `#${id}`
const rows = computed(() => shift.result?.assignments ?? [])

async function run() {
  await emp.fetchAll()
  await shift.generate(year.value, month.value)
  ;(shift.result?.warnings ?? []).forEach((w) => message.warning(w))
}
</script>

<template>
  <h2>{{ year }}年{{ month }}月 シフト</h2>
  <AvailabilityCalendar :year="year" :month="month" />
  <NButton type="primary" :loading="shift.generating" style="margin:16px 0" @click="run">
    シフトを自動生成
  </NButton>
  <p v-if="shift.result">状態: {{ shift.result.status }} / 割当 {{ rows.length }} 件</p>
  <table v-if="rows.length" border="1" cellpadding="6" style="border-collapse:collapse">
    <thead><tr><th>日付</th><th>従業員</th><th>シフト</th></tr></thead>
    <tbody>
      <tr v-for="(a, i) in rows" :key="i">
        <td>{{ a.target_date }}</td><td>{{ nameOf(a.employee_id) }}</td><td>{{ a.shift_type }}</td>
      </tr>
    </tbody>
  </table>
</template>
```

### 8-5. 動作確認

1. 第5章で従業員を**必要人数以上**登録（例: 8〜10 名。時給や `main_shift_type` は任意）。
2. `/shift` で「シフトを自動生成」をクリック。
3. 状態が `OPTIMAL` か `FEASIBLE` になり、割当表が出れば成功！🎉
4. カレンダーで誰かを「勤務不可」にして再生成 → その人がその日に入らないことを確認。

これで**現サイトのコア（従業員→希望→ルール→最適化生成）が一気通貫で動きました。**

---

## 第9章 祝日表示と仕上げ

### 9-1. 祝日 API

`backend/app/routers/holidays.py`:

```python
# backend/app/routers/holidays.py
import jpholiday
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/holidays", tags=["holidays"])

class Holiday(BaseModel):
    date: str
    name: str

@router.get("", response_model=list[Holiday])
def list_holidays(year: int, month: int | None = None):
    pairs = jpholiday.month_holidays(year, month) if month else jpholiday.year_holidays(year)
    return [Holiday(date=d.isoformat(), name=n) for d, n in pairs]
```

`main.py` に登録。`GET /api/holidays?year=2026&month=7` で `[{"date":"2026-07-20","name":"海の日"}]` が返ります。

### 9-2. カレンダーに祝日を反映

`AvailabilityCalendar.vue` に、祝日を取得して赤字表示する処理を足します（`holidays` を ref に保持し、`onMounted`/`watch` で取得、日付セルに祝日名を表示）。実装例は本リポジトリの [`AvailabilityCalendar.vue`](../frontend/src/components/AvailabilityCalendar.vue) がそのまま参考になります。

### 9-3. ここまでのフォルダ構成（完成形の目安）

```
myshifts/
├── backend/
│   ├── .venv/
│   ├── myshifts.db
│   └── app/
│       ├── main.py
│       ├── database.py
│       ├── models.py
│       ├── schemas.py
│       ├── routers/  (employees, rules, shifts, holidays)
│       └── services/ (scheduler, holidays)
└── frontend/
    └── src/
        ├── main.ts, App.vue
        ├── api/client.ts
        ├── router/index.ts
        ├── types.ts
        ├── stores/  (employee, shift)
        ├── components/AvailabilityCalendar.vue
        └── views/  (EmployeesView, RulesView, ShiftTableView)
```

**おめでとうございます！** 現サイトの中核をゼロから作り切りました。

---

## 第10章 拡張課題（本物に近づける）

コアが動いたら、本物との差分を 1 つずつ埋めていきましょう。各項目は「なぜ必要か」と「本物の該当コード」をセットにしています。**まず本物のコードを読み、真似て自分の `myshifts/` に移植する**のが最短の上達法です。

### 10-1. PostgreSQL + Alembic（本番の DB 運用）
- **なぜ**: SQLite は 1 ファイル DB で本番非対応。`create_all` はテーブル変更に弱い。
- **やること**: 接続を Postgres に変更し、Alembic でマイグレーション管理。
- **参考**: [`core/database.py`](../backend/app/core/database.py) / [`alembic/`](../backend/alembic) / README の「開発コマンド」。`docker-compose.yml` で Postgres を起動。

### 10-2. 認証（Google OAuth + 権限）
- **なぜ**: 誰でも従業員を消せては困る。管理者のみ許可したい。
- **やること**: ログインで JWT を発行し、`Depends` で「ログイン必須 / 管理者必須」を各 API に付ける。
- **参考**: [`auth/`](../backend/app/auth) / [`core/security.py`](../backend/app/core/security.py) / フロントの [`stores/auth.ts`](../frontend/src/stores/auth.ts) と `router` のガード。
- 解説は [`backend-guide-for-beginners.md`](./backend-guide-for-beginners.md) の「ログインと権限」章。

### 10-3. 生成結果の保存・確定・編集
- **なぜ**: 生成しっぱなしでは使えない。DB に保存し、手直しや確定（finalize）をしたい。
- **やること**: `Shift` / `ShiftAssignment` テーブルを追加し、生成時に保存・再生成で置換。手動編集の PUT を用意。
- **参考**: [`models/shift.py`](../backend/app/models/shift.py) / [`routers/shifts.py`](../backend/app/routers/shifts.py)。

### 10-4. 給与（人件費）計算
- **なぜ**: 深夜割増(25%)・交通費・保険判定など、実務に必要。
- **参考**: [`services/payroll.py`](../backend/app/services/payroll.py) / [`routers/payroll.py`](../backend/app/routers/payroll.py) / [`PayrollView.vue`](../frontend/src/views/PayrollView.vue)。

### 10-5. PDF / Excel 出力
- **なぜ**: 現場に配るには紙・表計算が要る。
- **参考**: [`services/export.py`](../backend/app/services/export.py)（reportlab / openpyxl）。

### 10-6. LLM 連携（自然言語で追加ルール）
- **なぜ**: 「田中さんは 15 日休み」と書くだけでシフトに反映したい。
- **やること**: メモを LLM に渡し、構造化制約（勤務不可・週上限）へ変換して scheduler に合流。
- **参考**: [`services/llm.py`](../backend/app/services/llm.py) と、それを取り込む [`scheduler.py`](../backend/app/services/scheduler.py)。制約と目的関数の詳細は [`calculation.md`](./calculation.md) と [`scheduler-source-explained.md`](./scheduler-source-explained.md)。

### 10-7. テスト・CI
- **なぜ**: 壊さず改修を続けるため。
- **参考**: バックエンド `backend/tests/`（pytest）、フロント `vitest`（[`views/__tests__/`](../frontend/src/views/__tests__)）。

---

## 次に読むとよいもの

- [`backend-guide-for-beginners.md`](./backend-guide-for-beginners.md) — 本物のバックエンドを層ごとに解説（初心者向け）
- [`scheduler-source-explained.md`](./scheduler-source-explained.md) — シフト生成コードを行単位で解説
- [`calculation.md`](./calculation.md) — 制約と目的関数の数式まとめ
- [`TUTORIAL.md`](./TUTORIAL.md) — 既存プロジェクトを理解し「機能追加できる」ための中〜上級ガイド
- `http://localhost:8000/docs` — 自分の API を触って動きを体感

困ったら、まず動いている**本物のリポジトリ**を正解として見比べてください。あなたが作った `myshifts/` との差分が、そのまま次の学習テーマになります。
