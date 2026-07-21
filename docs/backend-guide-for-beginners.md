# バックエンド ソースコード解説（Python 初心者向け）

このドキュメントは、**Python をこれから始める人**でも、このプロジェクトのバックエンド（`backend/` フォルダ）が「何を・どこで・どうやって」やっているかを理解できることを目標にしています。

まず全体像 → 必要な Python の前提知識 → フォルダの役割 → 実際のコード、の順で進みます。分からない用語が出てきても、最後の [用語集](#12-用語集) にまとめてあるので安心してください。

---

## 目次

1. [そもそもバックエンドとは？](#1-そもそもバックエンドとは)
2. [使っている主な道具（技術）](#2-使っている主な道具技術)
3. [このコードを読むための Python ミニ知識](#3-このコードを読むための-python-ミニ知識)
4. [フォルダ構成と役割](#4-フォルダ構成と役割)
5. [リクエストが処理される流れ](#5-リクエストが処理される流れ)
6. [入口: `main.py`](#6-入口-mainpy)
7. [設定: `core/config.py`](#7-設定-coreconfigpy)
8. [データベース接続: `core/database.py`](#8-データベース接続-coredatabasepy)
9. [テーブル定義: `models/`](#9-テーブル定義-models)
10. [入出力の形: `schemas/`](#10-入出力の形-schemas)
11. [URL と処理: `routers/`](#11-url-と処理-routers)
12. [ログインと権限: `auth/` と `security.py`](#12-ログインと権限-auth-と-securitypy)
13. [頭脳部分: `services/`](#13-頭脳部分-services)
14. [実例: 「従業員を1人追加する」リクエストの一生](#14-実例-従業員を1人追加するリクエストの一生)
15. [データベースの変更管理（Alembic）](#15-データベースの変更管理alembic)
16. [用語集](#16-用語集)

---

## 1. そもそもバックエンドとは？

Web アプリは大きく 2 つに分かれます。

- **フロントエンド**（`frontend/`）= ブラウザに表示される画面。ボタンやカレンダーなど、人が見て触る部分。
- **バックエンド**（`backend/`）= 画面の裏で動く「サーバー」。データを保存したり、計算したりする部分。

例えるなら **レストラン**です。

| レストラン | このアプリ |
| --- | --- |
| お客さん | ブラウザを使う人 |
| ウェイター（注文を受ける） | フロントエンド |
| 厨房（料理を作る） | **バックエンド** ← この解説の対象 |
| 食材倉庫 | データベース（PostgreSQL） |

フロントエンドが「シフトを作って！」と注文すると、バックエンドが従業員データを倉庫から取り出し、計算して、シフト表を作って返します。この「注文のやりとり」は **API**（後述）という決まった形式で行います。

---

## 2. 使っている主な道具（技術）

バックエンドは Python で書かれ、次の道具（ライブラリ＝便利な部品集）を使っています。まずは「名前と役割」だけ知っておけば十分です。

| 道具 | ひとことで言うと | このアプリでの役割 |
| --- | --- | --- |
| **FastAPI** | Python で API を作るフレームワーク | 「このURLに来たらこの処理」を定義する |
| **SQLAlchemy** | Python でデータベースを扱う道具（ORM） | Python のオブジェクト ⇄ DB のテーブルを変換 |
| **Pydantic** | データの形をチェックする道具 | 送られてきたデータが正しい形か検査 |
| **Alembic** | DB の設計変更を記録・適用する道具 | テーブルの追加・変更を管理 |
| **PostgreSQL** | データベース本体 | 従業員・シフトなどを保存 |
| **OR-Tools (CP-SAT)** | Google 製の最適化ソルバ | シフトの最適な組み合わせを計算 |
| **uv** | Python のパッケージ管理ツール | ライブラリのインストールや実行 |

> **フレームワークとは？** よく使う機能があらかじめ用意された「土台」のこと。ゼロから作らず、土台に自分のコードを乗せるだけでアプリが動きます。FastAPI はその土台です。

---

## 3. このコードを読むための Python ミニ知識

このコードで頻出する書き方だけ、先に説明します。ここが分かると読める量が一気に増えます。

### (a) 型ヒント（type hint）

```python
def add(a: int, b: int) -> int:
    return a + b
```

`a: int` は「a は整数（int）ですよ」という**メモ書き**。`-> int` は「この関数は整数を返す」という意味。**動作は変わりません**が、人間や道具が「どんなデータか」を理解しやすくなります。FastAPI や Pydantic はこのメモを読んで自動でチェックしてくれます。

よく出る型:
- `int`（整数）, `str`（文字列）, `bool`（真偽 True/False）, `float`（小数）
- `list[str]`（文字列のリスト）, `dict[str, int]`（キーが文字列・値が整数の辞書）
- `str | None` … 「文字列**または** None（空っぽ）」。`|` は「または」。

### (b) デコレータ（`@` で始まる行）

```python
@router.get("/employees")
def list_employees():
    ...
```

関数の上に付く `@なにか` を**デコレータ**と呼びます。「この関数に追加の役割を持たせる印」です。ここでは「`/employees` に GET リクエストが来たら、この関数を実行してね」と FastAPI に登録しています。

### (c) `async` / `await`

```python
async def google_callback(...):
    token = await exchange_code(code)
```

`async def` は「時間がかかる待ち処理（ネット通信など）を、待っている間ほかの処理を進められる関数」。`await` は「ここで結果を待つ」という印。**まずは「外部と通信するときに使うおまじない」**くらいの理解で大丈夫です。

### (d) クラスとデコレータ `@dataclass`

```python
class Employee:
    ...
```

**クラス**は「データと機能をまとめた設計図」。`Employee` クラスから作った 1 個 1 個が「従業員データ」になります。

```python
@dataclass
class EmployeeSpec:
    id: int
    name: str
```

`@dataclass` は「データを入れるだけの簡単なクラスを、少ない記述で作る」ための道具です。

### (e) デコレータ `@lru_cache` と `@property`

- `@lru_cache` … 一度計算した結果を覚えておいて、次回から使い回す（＝速くする）。
- `@property` … メソッド（関数）を、あたかも変数のように `obj.is_production` と書いて呼べるようにする。

---

## 4. フォルダ構成と役割

`backend/app/` の中は、役割ごとにフォルダが分かれています。これを **「層（レイヤー）で分ける」** と言い、大きなアプリを整理する定番の方法です。

```
app/
├── main.py           ← 【入口】アプリを起動し、全部をつなぐ
├── core/             ← 【土台】設定・DB接続・セキュリティ
│   ├── config.py         設定（環境変数の読み込み）
│   ├── database.py       データベースへの接続
│   └── security.py       パスワード暗号化・ログイン用トークン
├── models/           ← 【DBの形】テーブル1つ = クラス1つ（SQLAlchemy）
│   ├── user.py           ユーザー（ログインアカウント）
│   ├── employee.py       従業員・希望/勤務不可
│   ├── rule.py           シフトパターン・必要人数ルール
│   └── shift.py          シフト（月）・割り当て
├── schemas/          ← 【入出力の形】APIでやりとりするデータの検査役（Pydantic）
├── routers/          ← 【窓口】URLごとの処理（FastAPI）
│   ├── auth.py           ログイン
│   ├── employees.py      従業員の追加・編集・削除
│   ├── shifts.py         シフト生成・保存・出力
│   ├── rules.py          ルール設定
│   ├── payroll.py        人件費計算
│   └── holidays.py       祝日一覧
├── auth/             ← 【認証】Googleログイン・権限チェック
└── services/         ← 【頭脳】重い計算・外部連携のロジック
    ├── scheduler.py      シフト最適化（CP-SAT）
    ├── payroll.py        人件費の計算
    ├── llm.py            自然言語→制約（AI）
    ├── holidays.py       祝日判定
    └── export.py         PDF/Excel 出力
```

### 各層の関係（超重要）

```
リクエスト
   │
   ▼
routers（窓口）  ── 入出力の検査 → schemas
   │              権限チェック  → auth
   ▼
services（頭脳）  ── 重い計算・AI・PDF など
   │
   ▼
models（DBの形） ── 実際の保存/取得 → database（PostgreSQL）
```

**なぜ層に分けるの？** 役割がハッキリして、修正しやすく・壊れにくくなるからです。例えば「計算方法を変えたい」なら `services/` だけ見ればよく、`routers/`（窓口）はいじらずに済みます。

---

## 5. リクエストが処理される流れ

「シフトを作って」というリクエスト（`POST /api/shifts/generate`）を例に、ざっくりの流れを見ます。

```
1. ブラウザ → 「POST /api/shifts/generate」を送信
2. main.py がリクエストを受け取り、担当の router（shifts.py）へ渡す
3. auth が「この人は管理者か？」を確認（NGなら 403 拒否）
4. schemas が「送られてきたデータの形は正しいか？」を検査
5. router が models 経由でDBから 従業員・ルール・希望 を取得
6. services の scheduler が最適なシフトを計算
7. 結果を models 経由でDBに保存
8. schemas が「返すデータの形」を整えてブラウザへ返信
```

以降、この 1〜8 に登場する各ファイルを順に見ていきます。

---

## 6. 入口: `main.py`

アプリ全体の**入口**です。ここで「FastAPI アプリを作り」「各 router をつなげ」ます。

```python
app = FastAPI(
    title="AI-Shifts-Management API",
    version="0.1.0",
    docs_url="/docs",     # 自動生成される API ドキュメントの URL
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,                              # ブラウザからのアクセス許可設定
    allow_origins=[settings.frontend_origin],    # このフロントからのみ許可
    ...
)

app.include_router(auth.router, prefix="/api")       # /api/auth/... を有効化
app.include_router(employees.router, prefix="/api")  # /api/employees/... を有効化
app.include_router(shifts.router, prefix="/api")     # /api/shifts/... を有効化
# …他も同様
```

- **`app`** … これがアプリ本体。`uvicorn app.main:app` で起動されるのがこの `app`。
- **`include_router(...)`** … 各ファイルに分けて書いた窓口（router）を、まとめて登録する。`prefix="/api"` を付けているので、全 URL の頭に `/api` が付きます。
- **`CORSMiddleware`** … 「別アドレス（フロントの `localhost:5173`）からのアクセスを許可する」設定。これが無いとブラウザが安全のため通信をブロックします。
- **`/docs`** … ブラウザで `http://localhost:8000/docs` を開くと、**API の一覧と試せる画面**が自動で出ます（FastAPI の便利機能）。まず触ってみるのがおすすめ。

さらに、動作確認用の小さな窓口もここにあります:

```python
@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
```

`GET /api/health` に来たら `{"status": "ok", ...}` を返すだけ。「サーバー生きてる？」の確認用です。

---

## 7. 設定: `core/config.py`

パスワードや接続先などの**設定値**をまとめる場所です。これらは「環境変数」や `.env` ファイルから読み込みます（コードに直接パスワードを書かないのが安全のため）。

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", ...)  # .env から読む

    environment: Literal["development", "staging", "production"] = "development"
    secret_key: str = "insecure-default-change-me"
    database_url: str = "postgresql+psycopg://shifts:shifts_password@localhost:5432/shifts_db"
    frontend_origin: str = "http://localhost:5173"
    llm_provider: Literal["anthropic", "openai", "none"] = "anthropic"
    ...
```

- **`BaseSettings`**（Pydantic）… 環境変数や `.env` ファイルから自動で値を読み込むクラス。
- 右側の `= "..."` は**初期値**。`.env` に書いてあればそちらが優先されます。
- `Literal["development", ...]` … 「この 3 つの文字列のどれか」しか許さない、という制限。

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`get_settings()` を呼ぶと設定オブジェクトが得られます。`@lru_cache` のおかげで、何度呼んでも**最初の 1 回だけ**読み込み、以降は使い回します（速い）。

> 💡 前に `dev.sh` で「`.env` を読まないと DB 接続が localhost になって失敗した」問題がありましたが、その `env_file=".env"` の設定がここです。

---

## 8. データベース接続: `core/database.py`

Python から PostgreSQL に接続する準備をする場所です。

```python
engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, ...)

class Base(DeclarativeBase):
    """全 ORM モデルの親クラス"""

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- **`engine`** … データベースへの「回線」。接続先は `config.py` の `database_url`。
- **`Session`（セッション）** … DB とのやりとり 1 回分の「作業台」。ここでデータを追加・取得・保存します。
- **`Base`** … 後で出てくる **models（テーブル定義）の共通の親**。すべてのテーブルはこれを継承します。
- **`get_db()`** … リクエストごとに新しいセッションを作り、処理が終わったら閉じる関数。`yield`（一時的に値を渡す）を使い、**使い終わったら必ず `db.close()` する**仕組み。これを FastAPI の「依存（Depends）」として各窓口に配ります（後述）。

---

## 9. テーブル定義: `models/`

データベースの**テーブル（表）を Python のクラスで表現**したものです。この仕組みを **ORM（Object-Relational Mapping）** と呼びます。「SQL を直接書かず、Python のオブジェクトとして DB を扱える」のが利点です。

### 例: 従業員テーブル（`models/employee.py`）

```python
class Employee(Base):
    __tablename__ = "employees"          # 実際のDBテーブル名

    id: Mapped[int] = mapped_column(Integer, primary_key=True)   # 主キー（1件ごとの番号）
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 名前（必須）
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    hourly_wage: Mapped[int] = mapped_column(Integer, default=1100)  # 時給（初期値1100）
    main_shift_type: Mapped[str | None] = mapped_column(String(32))  # 得意シフト
    weekly_shifts: Mapped[int] = mapped_column(Integer, default=3)   # 週の希望回数
    active: Mapped[bool] = mapped_column(Boolean, default=True)      # 在籍中か
    ...
```

読み方:
- **`class Employee(Base)`** … 「`employees` テーブル」を表すクラス。`Base` を継承しているのがポイント。
- **`id: Mapped[int] = mapped_column(...)`** … 1 つの**列（カラム）**の定義。`Mapped[int]` が「型」、`mapped_column(...)` が「DB 上の細かい設定」。
- **`primary_key=True`** … 主キー。各行を区別する一意な番号（1, 2, 3, …）。
- **`nullable=False`** … 空（NULL）を許さない＝必須。`nullable=True` は空を許す。
- **`unique=True`** … 重複禁止（同じメールの人は 2 人いない、など）。
- **`default=1100`** … 何も指定しないときの初期値。

### テーブル同士のつながり（リレーション）

```python
availabilities: Mapped[list[EmployeeAvailability]] = relationship(
    "EmployeeAvailability", back_populates="employee", cascade="all, delete-orphan",
)
```

`relationship(...)` は「テーブル同士の関係」を表します。ここでは「1 人の従業員は複数の希望（availability）を持つ」という 1 対多の関係。`cascade="all, delete-orphan"` は「従業員を消したら、その希望も一緒に消す」という設定です。

### このアプリの主なテーブル

| モデル（クラス） | テーブル | 役割 |
| --- | --- | --- |
| `User` | users | ログインアカウント（admin / employee） |
| `Employee` | employees | 従業員（時給・週回数・得意シフトなど） |
| `EmployeeAvailability` | employee_availabilities | 希望日 / 勤務不可日 |
| `ShiftPattern` | shift_patterns | シフトの型（朝/夜/深夜など） |
| `StaffingRule` | staffing_rules | 「平日の朝は 2 人」などの必要人数 |
| `Shift` | shifts | ある月のシフト表（入れ物） |
| `ShiftAssignment` | shift_assignments | 「誰が・いつ・どのシフト」1 件ずつ |

`Enum`（列挙型）もよく出ます。例えば:

```python
class AvailabilityKind(StrEnum):
    unavailable = "unavailable"  # 絶対勤務不可
    preferred = "preferred"      # 入りたい
```

これは「決まった選択肢だけを許す型」。希望の種類は必ずこの 2 つのどちらか、という保証になります。

---

## 10. 入出力の形: `schemas/`

`models/` が「DB の形」なのに対し、`schemas/` は **「API でやりとりするデータの形」** です。Pydantic というライブラリで、**送られてきたデータの検査**と**返すデータの整形**を担います。

### なぜ models と分けるの？

DB の中身をそのまま外に出すと、パスワードなど**見せたくない情報まで漏れる**危険があります。また「入力時に必要な項目」と「DB に保存されている項目」は微妙に違います。だから**専用の入出力フォーマット**を別に用意します。

### 例（`schemas/employee.py`）

```python
class EmployeeBase(BaseModel):
    name: str
    email: EmailStr | None = None
    age: int | None = Field(default=None, ge=15, le=99)   # 15〜99 の範囲チェック
    hourly_wage: int = Field(default=1100, ge=0)          # 0 以上
    weekly_shifts: int = Field(default=3, ge=0, le=7)     # 0〜7
    ...

class EmployeeCreate(EmployeeBase):   # 「作成時」に受け取る形
    pass

class EmployeeUpdate(BaseModel):      # 「更新時」= 全部 任意（変えたい項目だけ送る）
    name: str | None = None
    ...

class EmployeeRead(EmployeeBase):     # 「返す時」の形
    model_config = ConfigDict(from_attributes=True)  # DBオブジェクトから変換OK
    id: int
```

読みどころ:
- **`BaseModel`** … Pydantic の基本クラス。これを継承すると自動でデータ検査が付く。
- **`Field(ge=15, le=99)`** … `ge` = 以上（≥）、`le` = 以下（≤）。範囲外の値は**自動で弾いてエラー**にしてくれる。`EmailStr` はメール形式かも検査。
- **`EmployeeCreate` / `EmployeeUpdate` / `EmployeeRead`** … 「作成用」「更新用」「返却用」で形を分けているのが定番パターン。
- **`from_attributes=True`** … SQLAlchemy の `Employee`（DBオブジェクト）から、そのまま `EmployeeRead` に変換してよい、という許可。

> つまり: **routers が受け取る入口で `...Create`/`...Update` が検査し、返す出口で `...Read` が整える。** DB の生データが直接外に出ないようにする番人です。

---

## 11. URL と処理: `routers/`

**「どの URL に来たら、何をするか」** を書く窓口です。FastAPI のデコレータ（`@router.get` など）で定義します。

### 基本パターン（`routers/employees.py` より）

```python
router = APIRouter(prefix="/employees", tags=["employees"])  # 頭に /employees が付く

@router.get("", response_model=list[EmployeeRead])
def list_employees(
    _user: CurrentUser,                          # ← ログイン必須（権限チェック）
    db: Annotated[Session, Depends(get_db)],     # ← DBセッションを受け取る
    active_only: bool = False,                   # ← URL の ?active_only=true を受け取る
):
    stmt = select(Employee).order_by(Employee.id)
    if active_only:
        stmt = stmt.where(Employee.active.is_(True))
    return list(db.execute(stmt).scalars())      # DBから取得して返す
```

超重要ポイント **「依存（Depends）」**:
- `db: Annotated[Session, Depends(get_db)]` … 「この処理には DB セッションが要る」と書くだけで、FastAPI が `get_db()` を呼んで**自動で用意**してくれます。これを **依存性注入（Dependency Injection）** と呼びます。
- `_user: CurrentUser` … 同様に「ログイン済みユーザー」を要求。中で**トークンを検証**し、無効なら自動で 401（未認証）を返します。頭に `_` が付くのは「受け取るけど中では直接使わない（＝ログインチェックが目的）」という慣習。

### 作成・更新・削除（CRUD）

```python
@router.post("", response_model=EmployeeRead, status_code=201)
def create_employee(payload: EmployeeCreate, _admin: AdminUser, db: ...):
    employee = Employee(**payload.model_dump())   # 受け取ったデータからDBオブジェクト生成
    db.add(employee)      # 追加予約
    db.commit()           # 確定（ここで実際にDBへ書き込み）
    db.refresh(employee)  # DBが採番した id などを取り込む
    return employee
```

- `payload: EmployeeCreate` … 送られてきた JSON を **`EmployeeCreate` で検査**して受け取る。おかしなデータはここで自動的に 422 エラー。
- `_admin: AdminUser` … **管理者のみ**許可（一般ユーザーは 403 拒否）。
- `db.add()` → `db.commit()` の 2 段階が DB 書き込みの基本。`commit` で確定します。
- `**payload.model_dump()` … Pydantic データを辞書に変換し、`Employee(name=..., email=..., ...)` のように展開して渡すテクニック。

CRUD（Create/Read/Update/Delete）は HTTP メソッドと対応します:

| やりたいこと | HTTP メソッド | 例 |
| --- | --- | --- |
| 一覧・取得 | GET | `@router.get("")` |
| 作成 | POST | `@router.post("")` |
| 一部更新 | PATCH | `@router.patch("/{employee_id}")` |
| 全置換 | PUT | `@router.put("/{shift_id}/assignments")` |
| 削除 | DELETE | `@router.delete("/{employee_id}")` |

`/{employee_id}` のように波括弧で書くと、URL の一部を**変数として受け取れます**（パスパラメータ）。

> **シフト生成の窓口** `routers/shifts.py` の `generate_shift()` はこのアプリの主役です。データを集めて `services/scheduler.py` に渡し、結果を保存します。その中身の詳しい解説は [`scheduler-source-explained.md`](./scheduler-source-explained.md) にあります。

---

## 12. ログインと権限: `auth/` と `security.py`

このアプリは **Google ログイン**を使います。パスワードを自前で預からず、「Google に本人確認してもらう」方式（OAuth）です。

### トークン（JWT）とは — `core/security.py`

ログイン後、サーバーは利用者に **トークン**という「入館証」を渡します。以降のリクエストはこの入館証を提示することで「誰か」を証明します。

```python
def create_access_token(subject: str, extra=None) -> str:
    payload = {"sub": subject, "iat": ..., "exp": ...}  # 誰の・いつ発行・いつ期限切れ
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, ...)  # 改ざんされていないか検証
```

- **JWT（ジョット）** … 中に「誰・期限」などを書き、サーバーの秘密鍵（`secret_key`）で署名した文字列。**改ざんするとバレる**ので安全。
- パスワードを扱う関数（`hash_password` / `verify_password`）もここにありますが、通常は Google ログインを使います。

### 権限チェック — `auth/deps.py`

```python
def get_current_user(token, db) -> User:
    if not token:
        raise HTTPException(401, "not authenticated")   # 入館証なし → 拒否
    payload = decode_token(token)                        # 入館証を検証
    user = db.execute(select(User).where(User.id == int(payload["sub"]))).scalar_one_or_none()
    ...
    return user

def require_admin(user=Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(403, "admin only")           # 管理者以外 → 拒否
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]  # 「ログイン必須」の合言葉
AdminUser   = Annotated[User, Depends(require_admin)]      # 「管理者必須」の合言葉
```

router 側では `_user: CurrentUser`（ログイン必須）や `_admin: AdminUser`（管理者必須）と**書くだけ**でチェックがかかります。これも依存（Depends）の仕組みです。

### Google ログインの流れ — `auth/google.py` + `routers/auth.py`

```
1. 利用者が「Googleでログイン」→ /api/auth/google/login
2. サーバーが Google のログイン画面URLへリダイレクト
3. 利用者が Google で認証 → Google が /api/auth/google/callback に戻す
4. サーバーが Google と通信して本人情報（メール等）を取得
5. その人を users テーブルに登録/更新し、JWT を発行
6. フロントに token 付きでリダイレクト
```

ちょっとした親切設計として、**一番最初に登録した人は自動で管理者（admin）**になります:

```python
is_first_user = db.execute(select(User).limit(1)).scalar_one_or_none() is None
...
role=UserRole.admin if is_first_user else UserRole.employee
```

また開発中だけ使える簡易ログイン `dev-login` もあります（本番環境では 404 で無効化）。

---

## 13. 頭脳部分: `services/`

routers が「窓口」なら、services は **「重い計算や外部連携を担う頭脳」** です。窓口をスッキリ保つため、複雑なロジックはここに分離します。

| ファイル | 役割 | ざっくり中身 |
| --- | --- | --- |
| `scheduler.py` | **シフト最適化** | OR-Tools (CP-SAT) で「誰をどこに入れるか」を計算 |
| `payroll.py` | **人件費計算** | 深夜割増(25%)・交通費・保険判定を集計 |
| `llm.py` | **AI で制約抽出** | 「今月の事情」文章 → 構造化された制約データ |
| `holidays.py` | **祝日判定** | `jpholiday` で土日・祝日を判定 |
| `export.py` | **書類出力** | シフト表を PDF / Excel に変換 |

### 例: 祝日判定（`services/holidays.py`）— 一番シンプル

```python
import jpholiday

def is_weekend_or_holiday(d: date) -> bool:
    return d.weekday() >= 5 or is_holiday(d)   # 土(5)・日(6) または 祝日

def category_for(d: date) -> str:
    return "weekend_or_holiday" if is_weekend_or_holiday(d) else "weekday"
```

`d.weekday()` は月曜=0 … 日曜=6 を返します。`>= 5` で土日、`jpholiday.is_holiday` で祝日を判定。シフトの必要人数は「平日 / 週末・祝日」で変わるので、この判定が使われます。

### 例: シフト最適化（`services/scheduler.py`）— このアプリの心臓部

「必要人数を満たしつつ、本人の希望や得意シフトをできるだけ叶える」最適な組み合わせを、**OR-Tools（CP-SAT）** という数学の道具で解きます。

考え方だけ超ざっくり:
- **決定変数** … 「従業員 e を 日 d の シフト p に入れる？（はい=1／いいえ=0）」を全組み合わせ用意。
- **ハード制約（絶対守る）** … ①1人1日1シフトまで ②勤務不可日は入れない ③必要人数ちょうど。
- **目的関数（なるべく良く）** … 週の希望回数に近づけ、希望日・得意シフトに入れたらご褒美（点数）。この点数が最良になる組み合わせをコンピュータが探します。

> 詳しい数式とコードの対応は [`calculation.md`](./calculation.md) と [`scheduler-source-explained.md`](./scheduler-source-explained.md) に分けてあります。まずは「難しい組み合わせ探しを自動でやってくれる部分」と理解すればOK。

### 例: AI 連携（`services/llm.py`）

「田中さんは 15 日休み」のような**自然な日本語**を、AI（Claude や GPT）に渡して**機械が扱えるデータ**に変換します。

```python
async def derive_constraints_from_text(note, employees_hint, year, month) -> dict:
    empty = {"hard_unavailable": [], "max_shifts_per_week_override": {}, "date_notes": {}, "warnings": []}
    if not note or not note.strip():
        return empty      # メモが空なら AI を呼ばない
    try:
        # 設定に応じて Claude または GPT を呼ぶ
        ...
    except Exception:
        logger.exception("LLM call failed; falling back to empty constraints")
    ...
    return empty          # 失敗しても空データを返す＝アプリは止まらない
```

ポイントは **「失敗しても全体を止めない」** こと。AI はあくまで補助なので、呼べなくても手動の希望だけでシフトは作れます。

---

## 14. 実例: 「従業員を1人追加する」リクエストの一生

ここまでの層が実際どう連携するか、`POST /api/employees` を例に最初から最後まで追います。

```
① ブラウザが送信:
   POST /api/employees
   Authorization: Bearer <トークン>
   本文: {"name": "田中太郎", "hourly_wage": 1200, "weekly_shifts": 4}

② main.py … /api で始まるので employees.router に渡す

③ routers/employees.py の create_employee() が呼ばれる:
   - _admin: AdminUser  → auth/deps.py がトークンを検証し「管理者か」チェック
       └ NGなら 401（未ログイン）/ 403（管理者でない）で即終了
   - payload: EmployeeCreate → schemas が本文を検査
       └ hourly_wage が負なら 422 で即終了（Field(ge=0) のおかげ）
   - db: Depends(get_db) → core/database.py が DBセッションを用意

④ DB 保存:
   employee = Employee(**payload.model_dump())   # models の Employee を生成
   db.add(employee); db.commit(); db.refresh(employee)

⑤ 返信:
   return employee  → response_model=EmployeeRead が
                      DBオブジェクトを安全な形（id付き）に整えて JSON化

⑥ ブラウザが受信:
   {"id": 7, "name": "田中太郎", "hourly_wage": 1200, "weekly_shifts": 4, ...}
```

**各層が 1 つずつ仕事をして、バケツリレーで処理が進む**のが分かれば、このコードベースはほぼ読めます。

---

## 15. データベースの変更管理（Alembic）

「従業員テーブルに新しい列を足したい」ときなど、**DB の設計変更を安全に記録・適用**するのが Alembic です。

- 変更履歴は `backend/alembic/versions/` にファイルとして残ります（1 変更 = 1 ファイル）。
- 適用コマンド: `uv run alembic upgrade head`（`dev.sh` が起動時に自動実行）。
- `models/` を書き換えたら `uv run alembic revision --autogenerate -m "説明"` で変更ファイルを自動生成できます。

> **なぜ必要？** 「自分のPCでは列を足したけど、本番DBには反映し忘れた」を防ぐため。変更を**履歴として残し、どの環境にも同じ手順で適用**できるようにする仕組みです。前の会話で出た「`alembic upgrade head`」がまさにこれです。

---

## 16. 用語集

| 用語 | 意味 |
| --- | --- |
| **API** | プログラム同士が決まった形式でやりとりする窓口。ここでは「URL に対してデータを送受信する仕組み」 |
| **エンドポイント** | API の個々の窓口（URL＋メソッドの組）。例: `GET /api/employees` |
| **フレームワーク** | アプリの土台となる部品集。ここでは FastAPI |
| **ライブラリ** | 特定の機能をまとめた部品。例: SQLAlchemy、Pydantic |
| **ORM** | Python のオブジェクトと DB のテーブルを相互変換する仕組み（SQLAlchemy） |
| **モデル (model)** | DB のテーブルを表す Python クラス |
| **スキーマ (schema)** | API でやりとりするデータの形と検査ルール（Pydantic） |
| **ルーター (router)** | URL ごとの処理をまとめたファイル（FastAPI） |
| **デコレータ** | 関数の上に付ける `@...`。関数に役割を追加する印 |
| **依存 (Depends) / DI** | 「この処理にはコレが必要」と書くと自動で用意される仕組み |
| **セッション (session)** | DB とのやりとり 1 回分の作業台 |
| **commit** | DB への変更を確定させること |
| **マイグレーション** | DB の設計変更を記録・適用すること（Alembic） |
| **トークン / JWT** | ログイン後に配られる「入館証」。誰か・期限を署名付きで持つ |
| **OAuth** | 「Google に本人確認してもらう」ログイン方式 |
| **CORS** | 別アドレスのフロントからのアクセスを許可する設定 |
| **環境変数 / .env** | パスワードなどをコード外に置く仕組み |
| **async / await** | 待ち時間のある処理を効率よく扱う書き方 |
| **CP-SAT / OR-Tools** | 最適な組み合わせを数学的に解く Google 製ソルバ |
| **LLM** | 大規模言語モデル（Claude / GPT などの AI） |

---

## 次に読むとよいもの

- [`scheduler-source-explained.md`](./scheduler-source-explained.md) … シフト生成のコードを行単位で解説
- [`calculation.md`](./calculation.md) … 制約と目的関数の数式的まとめ
- `http://localhost:8000/docs` … 実際に API を触って動きを体感（一番おすすめ）
