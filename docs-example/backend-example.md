# バックエンド ソースコード解説（FastAPI 初心者向け）

このドキュメントは、`backend/` ディレクトリのソースコードが「どのように動いているか」を、
**FastAPI や Python のウェブ開発を知らない人でも読めるように** 解説したものです。

対象読者:

- プログラミングの基礎（変数・関数・クラス）はなんとなく分かるが、サーバー開発は初めての人
- 「画面から送られてきたお願いを、サーバーがどう処理してデータベースに保存しているのか」を知りたい人

---

## 0. まず結論：このサーバーは何をしているか

このバックエンドは **「AIシフト管理」アプリの頭脳と倉庫** を担当しています。

- 従業員・シフトパターン・ルールなどのデータを **データベースに保存する**
- ログイン（Google 認証）を処理し、本人確認をする
- **AI と数理最適化でシフト表を自動生成する** ← このアプリの心臓部
- 人件費（給料・深夜割増・交通費・保険判定）を **計算する**
- シフト表を **PDF / Excel ファイルに変換して** 返す

サーバーの計算はすべてこのバックエンドで計算しています。

```
[ブラウザ(画面)]  ←→  [バックエンドAPI]  ←→  [データベース]
   Vue.js で作成         ★ここの解説★         PostgreSQL
                        FastAPI (Python)      データの倉庫
```

---

## 1. そもそも「API サーバー」とは？（超入門）

### 1-1. サーバーは「窓口の集まり」

バックエンドは、外から見ると **窓口（エンドポイント）がたくさん並んだ受付** です。
窓口は「URL」と「動詞（メソッド）」の組み合わせで区別されます。

| 動詞            | 意味               | 例                                             |
| --------------- | ------------------ | ---------------------------------------------- |
| `GET`           | ちょうだい（取得） | `GET /api/employees` → 従業員一覧をください    |
| `POST`          | 作って（新規登録） | `POST /api/employees` → 新しい従業員を追加して |
| `PATCH` / `PUT` | 書き換えて（更新） | `PATCH /api/employees/3` → 3番の人を更新して   |
| `DELETE`        | 消して（削除）     | `DELETE /api/employees/3` → 3番の人を削除して  |

フロントエンドが `api.get('/employees')` と呼ぶと、
サーバー側の `GET /api/employees` の窓口が反応して、データを返します。
**フロントの `api/client.ts` と、バックの `routers/` は一対一で対応している** と考えてください。

### 1-2. FastAPI とは

**FastAPI**（ファストエーピーアイ）は、Python でこの「窓口」を作るための道具です。
最大の特徴は **「関数の上に飾りを付けるだけで窓口ができる」** ことです。

```python
@router.get("/patterns")          # ← ① この飾り（デコレータ）が「窓口の住所」
def list_patterns(...):           # ← ② 普通の Python 関数
    return [...]                  # ← ③ 返した値が自動で JSON になって画面に届く
```

`@router.get(...)` の行を **デコレータ** と呼びます。
「この関数を `GET /patterns` の窓口として登録して」という意味の目印です。
戻り値の Python のリストや辞書は、FastAPI が **自動で JSON に変換** して返してくれます。

### 1-3. FastAPI のうれしい 3 つの自動化

1. **入力チェックが自動** … 「month は 1〜12 の整数」と書いておけば、
   13 が送られてきた時点でサーバーが自動で拒否します（第 5 章）
2. **API ドキュメントが自動生成** … サーバーを起動して
   `http://localhost:8000/docs` を開くと、全窓口の一覧と試し打ち画面が出ます
3. **依存性注入（Depends）が自動** … 「この窓口を使う人はログイン必須」を
   1 行書くだけで実現できます（第 6 章）

---

## 2. プロジェクト全体の地図

`backend/` の中身と、それぞれの役割です。

```
backend/
├── pyproject.toml        ← 使うライブラリ一覧・設定（Python版の package.json）
├── Dockerfile            ← サーバーを箱詰めして動かすためのレシピ
├── .env.example          ← 環境変数（パスワード等）の記入例
├── alembic/              ← データベースの「設計変更履歴」
│   └── versions/
│       └── 0001_initial.py
└── app/
    ├── main.py           ← アプリの起動スイッチ（一番最初に動く）
    │
    ├── core/             ← 土台となる共通機能
    │   ├── config.py       設定の読み込み（環境変数）
    │   ├── database.py     データベース接続
    │   └── security.py     トークンの発行・検証
    │
    ├── models/           ← データベースの「表」の定義
    │   ├── user.py         ログインアカウント
    │   ├── employee.py     従業員・希望休
    │   ├── shift.py        シフト表・割り当て
    │   └── rule.py         シフトパターン・必要人員
    │
    ├── schemas/          ← 「やり取りするデータの形」の定義
    │   ├── auth.py / employee.py / shift.py / rule.py / payroll.py
    │
    ├── routers/          ← 窓口（エンドポイント）の定義
    │   ├── auth.py         ログイン関係
    │   ├── employees.py    従業員 CRUD
    │   ├── rules.py        ルール設定
    │   ├── shifts.py       シフト生成・取得・出力
    │   ├── payroll.py      人件費計算
    │   └── dev.py          開発用（テストデータ投入）
    │
    ├── auth/             ← 認証のしくみ
    │   ├── google.py       Google と通信する係
    │   └── deps.py         「ログイン必須」「管理者限定」の関所
    │
    ├── services/         ← 実際の頭脳（ビジネスロジック）
    │   ├── scheduler.py    ★ CP-SAT でシフトを自動生成
    │   ├── llm.py          ★ AI が自然文を制約に変換
    │   ├── payroll.py      人件費の計算
    │   ├── export.py       PDF / Excel の作成
    │   └── holidays.py     日本の祝日判定
    │
    └── tests/            ← 自動テスト
```

**大まかな役割分担**を一言でいうと：

- **routers** = 窓口（受付係。お願いを受け取って、担当に振る）
- **models** = データベースの表の設計図
- **schemas** = 外とやり取りする JSON の形の設計図
- **services** = 実際に計算する頭脳
- **core** = 設定・DB接続・トークンなどの土台
- **auth** = 「あなた誰？」を確認する関所

> **重要な設計方針**：`routers`（窓口）には **難しい計算を書きません**。
> 窓口は「データを DB から集めて → services にお願いして → 結果を返す」だけ。
> 計算の中身は全部 `services` にあります。こうしておくと、
> 計算部分だけを単体でテストできる（`tests/test_payroll.py` 参照）ためです。

---

## 3. サーバーが起動するまでの流れ

### ステップ①：`app/main.py`（起動スイッチ）

サーバーを起動すると、最初にこのファイルが動きます。

```python
app = FastAPI(
    title="AI-Shifts-Management API",
    docs_url="/docs",        # ← 自動生成ドキュメントの場所
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],   # 画面(localhost:5173)からの通信を許可
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")       # ログイン窓口を登録
app.include_router(employees.router, prefix="/api")  # 従業員窓口を登録
app.include_router(rules.router, prefix="/api")
app.include_router(shifts.router, prefix="/api")
app.include_router(payroll.router, prefix="/api")
app.include_router(dev.router, prefix="/api")
```

やっていることは 3 つだけです。

1. **`FastAPI()` でアプリ本体を作る**
2. **CORS の設定** … ブラウザは安全のため「別のアドレスへの通信」を標準でブロックします。
   画面は `localhost:5173`、サーバーは `localhost:8000` と **アドレスが違う** ため、
   「この画面からの通信は許可します」と明示的に宣言する必要があります。
   これが **CORS（コルス）** の設定です。これを忘れると画面から通信できません。
3. **`include_router` で窓口をまとめて登録** … 各ファイルに分けて書いた窓口を
   本体にくっつけます。`prefix="/api"` により、すべての URL の先頭に `/api` が付きます。

```python
@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
```

`/api/health` は **生存確認用の窓口** です。
「サーバーは生きてますか？」と聞くと `{"status": "ok"}` と返します。
デプロイ先（AWS 等）が定期的にここを叩いて、サーバーの死活を監視します。

### ステップ②：`core/config.py`（設定の読み込み）

パスワードや API キーを **コードに直接書くのは厳禁** です（GitHub に公開されてしまう）。
そこで、それらは `.env` という別ファイルに書き、そこから読み込みます。

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    environment: Literal["development", "staging", "production"] = "development"
    secret_key: str = "insecure-default-change-me"
    database_url: str = "postgresql+psycopg://shifts:...@localhost:5432/shifts_db"
    frontend_origin: str = "http://localhost:5173"
    google_client_id: str = ""
    anthropic_api_key: str = ""
    ...
```

`BaseSettings` を継承すると、**環境変数や `.env` ファイルから自動で値を読み込んで**
くれます。`= "..."` の部分は「書かれていなかった場合の初期値」です。

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

> `@lru_cache` は **「一度計算した結果を覚えておいて、2 回目以降は使い回す」** という飾りです。
> 設定ファイルの読み込みは 1 回で十分なので、何度 `get_settings()` を呼んでも
> **実際に読むのは初回だけ** になります。

`Literal["development", "staging", "production"]` は
**「この 3 つの文字列しか入れられない」** という指定です（フロントの `ShiftStatus` と同じ考え方）。

### ステップ③：`core/database.py`（データベース接続）

```python
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

登場人物は 4 つです。

| 名前                         | 役割                 | たとえ     |
| ---------------------------- | -------------------- | ---------- |
| `engine`（エンジン）         | DB への接続の管理者  | 電話回線   |
| `SessionLocal`（セッション） | 1 回分の会話         | 1 本の通話 |
| `Base`                       | すべての表の親クラス | 表のひな形 |
| `get_db()`                   | 通話を貸し出す係     | 電話交換手 |

`get_db()` の `yield`（イールド）は **「ここで一旦相手に渡して、終わったら戻ってくる」**
という特殊な `return` です。窓口の処理が終わると必ず `finally` に戻り、
`db.close()` で通話を切ります。**接続の閉じ忘れが起きない** のが利点です。

> `pool_pre_ping=True` は「使う前に一度 “もしもし” と確認する」設定です。
> 長時間放置して切れていた接続を掴んでしまう事故を防ぎます。

---

## 4. データベースの表：モデル（`models/`）

### 4-1. ORM とは

データベースを操作するには本来 **SQL** という別の言語が必要です。

```sql
SELECT * FROM employees WHERE active = true;
```

これを Python のまま書けるようにする仕組みが **ORM**（オーアールエム）で、
このプロジェクトでは **SQLAlchemy**（エスキューエルアルケミー）を使っています。

```python
select(Employee).where(Employee.active.is_(True))   # ← 上の SQL と同じ意味
```

**「データベースの 1 つの表 = Python の 1 つのクラス」「表の 1 行 = そのクラスの 1 個のオブジェクト」**
と対応させるのが ORM の考え方です。

### 4-2. 表の定義の読み方（`Employee` を例に）

```python
class Employee(Base):
    __tablename__ = "employees"           # ← DB 上の表の名前

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    hourly_wage: Mapped[int] = mapped_column(Integer, default=1100, nullable=False)
    main_shift_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    weekly_shifts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

1 行が 1 つの列（カラム）です。書式は
`列名: Mapped[Python の型] = mapped_column(DB の型, オプション...)`。

| オプション         | 意味                                             |
| ------------------ | ------------------------------------------------ |
| `primary_key=True` | この列が「行を一意に識別する番号」（ID）         |
| `nullable=False`   | 空っぽ（NULL）を許さない＝必須項目               |
| `unique=True`      | 重複禁止（同じメールアドレスの人は登録できない） |
| `default=1100`     | 指定しなかったときの初期値                       |
| `String(100)`      | 最大 100 文字の文字列                            |

### 4-3. 表と表のつながり（リレーション）

現実のデータは互いに関係しています。「この割り当ては、この従業員のもの」など。

```python
class ShiftAssignment(Base):
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    employee: Mapped[Employee] = relationship("Employee", back_populates="assignments")
```

- **`ForeignKey`（外部キー）** = 「この列には employees 表の id が入ります」という宣言。
  存在しない従業員番号を入れようとすると、DB がエラーで弾いてくれます。
- **`ondelete="CASCADE"`** = 「従業員が削除されたら、その人のシフト割り当ても一緒に消す」。
  持ち主のいない孤児データが残るのを防ぎます。
- **`relationship`** = Python 側から `assignment.employee.name` のように
  **たどれるようにする** 設定。裏で自動的に SQL を発行してくれます。

`back_populates` は「向こう側からもたどれるように」という相互リンクの指定です。

```python
# Employee 側
assignments: Mapped[list[ShiftAssignment]] = relationship(back_populates="employee")
```

これで `employee.assignments` （その人の全シフト）も `assignment.employee` （担当者）も
どちらからでもたどれます。

### 4-4. このアプリの表の全体像

```
users（ログインアカウント）
  │ employee_id
  ↓
employees（従業員）───────┬──→ employee_availabilities（休み希望／出勤希望）
  ↑                       │
  │ employee_id           └──→ shift_assignments（誰がいつ何のシフトか）
  │                                    ↑ shift_id
  │                              shifts（月ごとのシフト表）
  │
shift_patterns（朝/夜/深夜の時間定義）
staffing_rules（平日の朝は2人…という必要人員）
```

| 表                        | 保管しているもの                           | ファイル             |
| ------------------------- | ------------------------------------------ | -------------------- |
| `users`                   | ログインする人（Google アカウント紐付け）  | `models/user.py`     |
| `employees`               | 従業員の名前・時給・交通費・週何回入るか   | `models/employee.py` |
| `employee_availabilities` | 「この日は休みたい／入りたい」             | `models/employee.py` |
| `shifts`                  | 「2026年8月のシフト表」という入れ物        | `models/shift.py`    |
| `shift_assignments`       | 「8/1に田中さんが朝シフト」という 1 マス分 | `models/shift.py`    |
| `shift_patterns`          | 「朝 = 09:00-17:00」というパターン定義     | `models/rule.py`     |
| `staffing_rules`          | 「平日の朝は 2 人必要」というルール        | `models/rule.py`     |

> **`users` と `employees` はなぜ別なのか？**
> 「ログインできる人」と「シフトに入る人」は必ずしも一致しないためです。
> 店長（ログインするが自分はシフトに入らない）や、
> アルバイト（シフトには入るがアカウントは未登録）がありえます。
> そこで別の表にして、`users.employee_id` で紐づけています。

### 4-5. `StrEnum` — 決まった値しか入れない

```python
class ShiftStatus(StrEnum):
    draft = "draft"           # 下書き
    published = "published"   # 公開中
    finalized = "finalized"   # 確定済み
```

「シフトの状態はこの 3 つのどれか」と決めた **選択肢の一覧** です。
フロントの `ShiftStatus = 'draft' | 'published' | 'finalized'` と同じものが
バックエンドにもあり、**両者で同じ値を使う** ことで齟齬を防いでいます。

---

## 5. やり取りの形：スキーマ（`schemas/`）

### 5-1. なぜモデルとは別に必要なのか

`models` は **DB の表**、`schemas` は **外(画面)とやり取りする JSON の形** です。
似ていますが、**分ける理由があります**。

- DB には保存するが **外には出したくない** 項目がある（パスワードのハッシュなど）
- 外から **受け取っていい項目を限定したい**（`id` や `created_at` はサーバーが決めるので、
  画面から送られてきても無視すべき）
- **入力チェックのルールを書きたい**（年齢は 15〜99、時給は 0 以上、など）

そこで **Pydantic**（パイダンティック）というライブラリでこの「形」を定義します。

### 5-2. Create / Update / Read の 3 兄弟

`schemas/employee.py` は同じ従業員データに対して 3 つの形を用意しています。

```python
class EmployeeBase(BaseModel):
    name: str
    email: EmailStr | None = None
    age: int | None = Field(default=None, ge=15, le=99)      # 15以上99以下
    transport_cost: int = Field(default=0, ge=0)             # 0以上
    hourly_wage: int = Field(default=1100, ge=0)
    weekly_shifts: int = Field(default=3, ge=0, le=7)        # 週0〜7回
    active: bool = True


class EmployeeCreate(EmployeeBase):      # 【新規登録】用：id は不要
    pass


class EmployeeUpdate(BaseModel):         # 【更新】用：全部が省略可能
    name: str | None = None
    hourly_wage: int | None = Field(default=None, ge=0)
    ...


class EmployeeRead(EmployeeBase):        # 【返却】用：id が付く
    model_config = ConfigDict(from_attributes=True)
    id: int
```

| クラス           | いつ使う                | ポイント                                   |
| ---------------- | ----------------------- | ------------------------------------------ | --------------------------------- |
| `EmployeeCreate` | 画面 → サーバー（登録） | `id` を含まない（サーバーが採番するため）  |
| `EmployeeUpdate` | 画面 → サーバー（更新） | 全項目が `                                 | None` ＝ **送られた項目だけ更新** |
| `EmployeeRead`   | サーバー → 画面（返却） | `id` 付き。DB のオブジェクトから変換できる |

`ge=15, le=99` は **greater-equal（以上）/ less-equal（以下）** の略です。
`age: 200` が送られてくると、**関数が呼ばれる前に** FastAPI が
`422 Unprocessable Entity` エラーを返して弾きます。
**自分でチェックのコードを書く必要がありません。**

`model_config = ConfigDict(from_attributes=True)` は
**「SQLAlchemy のオブジェクトから直接変換していいよ」** という許可です。
これがあるので、窓口は DB から取ってきた `Employee` をそのまま `return` でき、
FastAPI が自動で `EmployeeRead` の形（＝JSON）に整えてくれます。

### 5-3. `exclude_unset` — 送られた項目だけ更新

更新窓口ではこの書き方が肝になります。

```python
updates = payload.model_dump(exclude_unset=True)   # ← 送られてきた項目だけ取り出す
for key, value in updates.items():
    setattr(employee, key, value)                  # ← その項目だけ上書き
```

`exclude_unset=True` を付けると、**画面が明示的に送った項目だけ** が辞書に入ります。
これがないと、送られなかった項目まで `None` で上書きしてしまい、
「名前だけ変えたつもりが時給が消えた」という事故が起きます。

---

## 6. 認証のしくみ（`auth/` と `core/security.py`）

### 6-1. トークンとは（おさらい）

ログインすると、サーバーは **JWT（ジョット）** という「署名付きの通行証」を発行します。
以降、画面は毎回この通行証を提示し、サーバーは署名を検証して本人確認します。

```
[画面] ログイン ──────────→ [サーバー] 本人確認OK
[画面] ←──── トークン発行 ── [サーバー]
[画面] トークン + お願い ───→ [サーバー] 署名を検証 → 処理実行
```

### 6-2. トークンの発行（`core/security.py`）

```python
def create_access_token(subject: str, extra: dict | None = None) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,                                        # 誰のものか（ユーザーID）
        "iat": int(now.timestamp()),                           # いつ発行したか
        "exp": int((now + timedelta(minutes=1440)).timestamp()),  # いつ切れるか
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")
```

トークンの中身は単なる **辞書（JSON）** です。ここに「ユーザーID」「発行時刻」
「有効期限（24時間後）」を書き、**秘密鍵で署名** して 1 本の文字列にします。

**重要**：トークンの中身は暗号化されていません（誰でも読めます）。
署名が守っているのは秘密ではなく **「改ざんされていないこと」** です。
`sub` を勝手に別のユーザー ID に書き換えても、署名が合わなくなって検証で弾かれます。
だからこそ、`secret_key` は絶対に外部に漏らしてはいけません。

```python
def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("invalid token") from exc
```

検証時は、署名が違う場合も **期限切れの場合も** 例外になります。

### 6-3. 関所（`auth/deps.py`）— FastAPI の最重要機能

FastAPI には **依存性注入（Depends）** という仕組みがあります。
「この窓口を使う前に、必ずこの関数を通してください」という指定です。

```python
def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],   # リクエストからトークンを抜き出す
    db: Annotated[Session, Depends(get_db)],                # DB 接続を借りる
) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="not authenticated")
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user_id = payload.get("sub")
    user = db.execute(select(User).where(User.id == int(user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="user not found")
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="admin only")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]   # ← 「ログイン必須」の合図
AdminUser = Annotated[User, Depends(require_admin)]        # ← 「管理者限定」の合図
```

`get_current_user` は **「トークンを読んで、DB からその人を探して返す」** 関数です。
どこかで失敗したら `HTTPException` を投げて、その時点で処理を打ち切ります。

最後の 2 行が便利ポイントです。これで窓口側は **たった 1 行** 書くだけで済みます。

```python
@router.post("", response_model=EmployeeRead)
def create_employee(
    payload: EmployeeCreate,
    _admin: AdminUser,        # ← ★これだけで「管理者しか実行できない窓口」になる★
    db: Annotated[Session, Depends(get_db)],
):
    ...
```

`_admin` という引数を書いた瞬間に、FastAPI が **関数を実行する前に**
「トークンある？ → 有効？ → その人は管理者？」を全部チェックしてくれます。
条件を満たさなければ関数は **一度も呼ばれません**。

> 変数名の頭の `_`（アンダースコア）は
> **「受け取るけど関数の中では使わない」** という Python の慣習です。
> ここでは「チェックのためだけに書いている」ことを表しています。

| 状態                     | 返るコード         | 意味                                     |
| ------------------------ | ------------------ | ---------------------------------------- |
| トークンなし・期限切れ   | `401 Unauthorized` | 「あなた誰？」                           |
| ログイン済みだが権限不足 | `403 Forbidden`    | 「あなたは分かるが、それは許可できない」 |

フロントの `client.ts` が `401` を受け取ったらログイン画面に飛ばすのは、この `401` です。

### 6-4. Google ログインの流れ（`auth/google.py` + `routers/auth.py`）

```
① 画面「Googleでログイン」クリック
      ↓
② GET /api/auth/google/login
   サーバーが Google の認証ページ URL を組み立ててリダイレクト
      ↓
③ ユーザーが Google の画面でアカウントを選んで承認
      ↓
④ Google が GET /api/auth/google/callback?code=xxxx にリダイレクトして戻す
      ↓
⑤ サーバーが code を Google に送り、アクセストークンと交換（exchange_code）
      ↓
⑥ そのトークンでユーザー情報（メール・名前・写真）を取得（fetch_userinfo）
      ↓
⑦ DB に users のレコードを作成 or 更新（_persist_or_update_user）
      ↓
⑧ 自前の JWT を発行し、画面の /auth/callback?token=... にリダイレクト
```

これは **OAuth 2.0 認可コードフロー** という標準的な手順です。
ポイントは **「パスワードがこのサーバーを一度も通らない」** こと。
ユーザーは Google の画面にだけパスワードを入れるので、
このアプリがパスワードを漏らす事故が原理的に起きません。

`_persist_or_update_user` には 2 つの仕掛けがあります。

```python
domain = email.split("@")[-1]
if settings.allowed_google_domain and domain != settings.allowed_google_domain:
    raise HTTPException(status_code=403, detail=...)
```

**ドメイン制限**：`ALLOWED_GOOGLE_DOMAIN` を設定すると、
そのドメインのメールアドレスの人しかログインできなくなります（社内限定運用向け）。

```python
is_first_user = db.execute(select(User).limit(1)).scalar_one_or_none() is None
...
role=UserRole.admin if is_first_user else UserRole.employee,
```

**最初の 1 人は自動で管理者**：まだ誰も登録されていなければ `admin` になります。
初期セットアップ時に「管理者を作る管理者がいない」という鶏と卵の問題を回避する定番の手です。

---

## 7. 窓口の実際（`routers/`）

### 7-1. 典型的な窓口の形（`routers/employees.py`）

```python
router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeRead])
def list_employees(
    _user: CurrentUser,                             # ログイン必須
    db: Annotated[Session, Depends(get_db)],        # DB 接続を借りる
    active_only: bool = False,                      # ← URL のクエリパラメータ
):
    stmt = select(Employee).order_by(Employee.id)
    if active_only:
        stmt = stmt.where(Employee.active.is_(True))
    return list(db.execute(stmt).scalars())
```

- `APIRouter(prefix="/employees")` … この中の窓口は全部 `/employees` で始まる
- `tags=["employees"]` … `/docs` の自動ドキュメントでのグループ分け用のラベル
- `response_model=list[EmployeeRead]` … **返す形の宣言**。DB オブジェクトを
  そのまま `return` しても、FastAPI がこの形に整えて JSON にしてくれる
- `active_only: bool = False` … 関数の引数に書くだけで
  `GET /api/employees?active_only=true` というクエリパラメータになる

> `db.execute(stmt).scalars()` の `scalars()` は
> 「1 行を `(Employee,)` というタプルではなく `Employee` そのもので取り出す」指定です。
> 決まり文句だと思って構いません。

### 7-2. 作成・更新・削除

```python
@router.post("", response_model=EmployeeRead, status_code=201)
def create_employee(payload: EmployeeCreate, _admin: AdminUser, db: ...):
    employee = Employee(**payload.model_dump())   # ① スキーマ → モデルに詰め替え
    db.add(employee)                              # ② 「追加します」と予告
    db.commit()                                   # ③ ★確定（ここで実際に DB へ書く）★
    db.refresh(employee)                          # ④ 採番された id を読み直す
    return employee
```

**`db.commit()` を呼ぶまで DB には反映されません。** これがトランザクションです。
複数の変更をまとめて「全部成功か、全部なかったことに」できます。

`db.refresh()` は「DB が自動で決めた値（`id` や `created_at`）を読み直す」処理です。
これをしないと、返す `employee` の `id` が空のままになります。

`status_code=201` は **「作成しました」** を表す HTTP ステータスです
（単なる成功の `200` と区別する慣習）。削除は `204 No Content`（成功、返す中身なし）。

```python
@router.delete("/{employee_id}", status_code=204)
def delete_employee(employee_id: int, _admin: AdminUser, db: ...):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="employee not found")
    db.delete(employee)
    db.commit()
```

URL の `{employee_id}` の部分は **パスパラメータ** で、そのまま引数になります。
`employee_id: int` と型を書いておくと、`/employees/abc` のような
数字でない URL は FastAPI が自動で弾きます。

見つからなければ `404 Not Found` を返すのが約束事です。

### 7-3. 主な窓口の一覧

| メソッド | URL                             | 権限       | 何をするか                 |
| -------- | ------------------------------- | ---------- | -------------------------- |
| `GET`    | `/api/health`                   | 誰でも     | 生存確認                   |
| `GET`    | `/api/auth/google/login`        | 誰でも     | Google 認証へリダイレクト  |
| `GET`    | `/api/auth/me`                  | ログイン   | 自分の情報を返す           |
| `POST`   | `/api/auth/dev-login`           | 開発時のみ | 開発用の簡易ログイン       |
| `GET`    | `/api/employees`                | ログイン   | 従業員一覧                 |
| `POST`   | `/api/employees`                | **管理者** | 従業員追加                 |
| `PATCH`  | `/api/employees/{id}`           | **管理者** | 従業員更新                 |
| `DELETE` | `/api/employees/{id}`           | **管理者** | 従業員削除                 |
| `POST`   | `/api/employees/availabilities` | ログイン   | 休み希望の登録             |
| `GET`    | `/api/rules/patterns`           | ログイン   | シフトパターン一覧         |
| `PUT`    | `/api/rules/staffing`           | **管理者** | 必要人員をまるごと差し替え |
| `GET`    | `/api/shifts?year=&month=`      | ログイン   | 指定月のシフト取得         |
| `POST`   | `/api/shifts/generate`          | **管理者** | ★ AI でシフト自動生成 ★    |
| `PUT`    | `/api/shifts/{id}/assignments`  | **管理者** | 手動で割り当てを差し替え   |
| `POST`   | `/api/shifts/{id}/finalize`     | **管理者** | シフトを確定状態にする     |
| `GET`    | `/api/shifts/{id}/export/pdf`   | ログイン   | PDF ダウンロード           |
| `GET`    | `/api/shifts/{id}/export/excel` | ログイン   | Excel ダウンロード         |
| `GET`    | `/api/payroll?year=&month=`     | ログイン   | 人件費レポート             |
| `POST`   | `/api/dev/seed` / `/reset`      | 開発時のみ | テストデータ投入 / 初期化  |

> **`PUT /rules/staffing` が「まるごと差し替え」なのはなぜ？**
> 必要人員は「平日×朝/夜/深夜」「休日×朝/夜/深夜」の 6 個で 1 セットの設定だからです。
> 1 個ずつ更新するより、6 個まとめて上書きするほうが単純で、
> 中途半端な状態になりません（`routers/rules.py` の `replace_staffing`）。

---

## 8. 頭脳①：シフト自動生成（`services/scheduler.py`）★このアプリの核心★

### 8-1. これは何をしている？

「25 人の従業員を、1 か月 31 日 × 3 種類のシフトに、
すべてのルールを守りながら割り当てる」という問題を解いています。

組み合わせの数は天文学的です。人間が手で総当たりするのは不可能ですし、
「ランダムに置いてみて、ダメならやり直す」方式でも現実的な時間で終わりません。

そこで **CP-SAT ソルバー**（Google の OR-Tools に入っている制約解決エンジン）を使います。

### 8-2. 制約プログラミングという考え方

普通のプログラムは **「どう計算するか」** を書きます。
制約プログラミングは **「何を満たしてほしいか」だけを書いて、探し方はソルバーに任せます。**

数独を思い浮かべてください。あなたはソルバーに
「各行に 1〜9 が 1 個ずつ」「各列も」「各ブロックも」というルールだけを伝えます。
**どの順番でマスを埋めるかは指示しません。** ソルバーが勝手に見つけてきます。

このアプリでも同じことをしています。

### 8-3. 変数の定義

```python
# x[e, d, p] = 1 なら「従業員 e が d 日に p のシフトに入る」、0 なら入らない
x: dict[tuple[int, date, int], cp_model.IntVar] = {}
for e in emps:
    for d in days:
        for p in pats:
            x[(e.id, d, p.id)] = model.NewBoolVar(f"x_e{e.id}_d{d}_p{p.code}")
```

**0 か 1 しか取らない変数（BoolVar）を、従業員 × 日 × パターンの数だけ用意します。**
25 人 × 31 日 × 3 パターン = **2,325 個** の変数です。
ソルバーの仕事は、この 2,325 個すべてに 0 か 1 を、ルールを守りつつ埋めることです。

### 8-4. ハード制約（絶対に守る）

```python
# ① 1 人 1 日 1 シフトまで（掛け持ち禁止）
for e in emps:
    for d in days:
        model.Add(sum(x[(e.id, d, p.id)] for p in pats) <= 1)
```

「その人のその日の変数を全部足したら 1 以下」＝ 多くても 1 個しか 1 にならない、
という書き方で「1 日 1 シフトまで」を表現しています。

```python
# ② 休み希望の日は入れない
for e in emps:
    for d in days:
        if (e.id, d) in unavailable:
            for p in pats:
                model.Add(x[(e.id, d, p.id)] == 0)
```

「0 で固定」してしまえば、ソルバーは絶対にその日を選べません。

```python
# ③ 必要人員をぴったり満たす
for d in days:
    day_cat = category_for(d)                        # weekday か weekend_or_holiday か
    for shift_cat in ("morning", "evening", "night"):
        required = self.staffing_rules.get((day_cat, shift_cat), 0)
        pats_in_cat = [p for p in pats if p.category == shift_cat]
        total = sum(x[(e.id, d, p.id)] for e in emps for p in pats_in_cat)
        model.Add(total == required)                 # ← == なので過不足なし
```

これが一番重要な制約です。「8/1（土）の朝シフトに入る人の合計は、ちょうど 3 人」。
`>=` ではなく `==` なので、**多すぎても許されません**（人件費の無駄を防ぐため）。

`category_for(d)` は `services/holidays.py` の関数で、
**土日または日本の祝日なら `weekend_or_holiday`** を返します。

```python
def is_weekend_or_holiday(d: date) -> bool:
    return d.weekday() >= 5 or is_holiday(d)   # 5=土, 6=日 / jpholiday で祝日判定
```

`jpholiday` ライブラリのおかげで、「海の日」のような移動祝日も自動で判定されます。

### 8-5. ソフト制約（できれば守る）

すべてを「絶対」にすると、条件が矛盾して **解が 1 つも見つからない** ことがあります。
そこで「守れたら嬉しい」条件は **点数** で表現します。

```python
# ① 週の希望勤務回数からのズレをペナルティに
for e in emps:
    weekly = max_shifts_override.get(e.id, e.weekly_target)
    monthly_target = weekly * (len(days) // 7 + (1 if len(days) % 7 else 0))
    total = sum(x[(e.id, d, p.id)] for d in days for p in pats)
    over = model.NewIntVar(0, len(days), f"over_e{e.id}")     # 多すぎた分
    under = model.NewIntVar(0, len(days), f"under_e{e.id}")   # 少なすぎた分
    model.Add(total - monthly_target == over - under)
    penalties.append(over)
    penalties.append(under)
```

「週 3 回希望」なら月の目標は約 15 回。実際が 18 回なら `over = 3`。
この `over`・`under` を **できるだけ小さくしたい値** として集めます。

```python
# ② 出勤希望日に入れたらボーナス
bonus_terms = [...]

# ③ メインシフト（その人の得意な時間帯）と一致したらボーナス
main_shift_bonus_terms = [...]
```

そして全部をひとつの式にまとめます。

```python
obj = 0
if penalties:
    obj += sum(penalties)                    # ペナルティは足す（小さくしたい）
if bonus_terms:
    obj -= 3 * sum(bonus_terms)              # ボーナスは引く（重み 3）
if main_shift_bonus_terms:
    obj -= 5 * sum(main_shift_bonus_terms)   # メインシフト一致は重み 5（最優先）
model.Minimize(obj)
```

`Minimize`（最小化）なので、**ペナルティは足し、ボーナスは引きます**。
`3` や `5` の数字が **優先度の重み** です。
`5 > 3` なので、「出勤希望日に入れる」より
**「その人の得意なシフト帯に入れる」ほうを優先する** 設計になっています。

> **重みの調整が運用のキモです。**
> 「希望休をもっと尊重してほしい」と言われたら、`bonus_terms` の重み 3 を上げる。
> ここの数字ひとつで、生成されるシフトの性格が変わります。

### 8-6. 解かせる

```python
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = self.max_solve_seconds   # 20秒でタイムアウト
solver.parameters.num_search_workers = 4                          # 4並列で探索
status = solver.Solve(model)
```

**20 秒の制限時間**が重要です。最適解を厳密に探すと何時間もかかる場合があるので、
「20 秒探して、その時点で見つかっている一番良い答えを使う」という方針にしています。

| status       | 意味                                           | どうなる   |
| ------------ | ---------------------------------------------- | ---------- |
| `OPTIMAL`    | 数学的に最適な解が見つかった                   | 採用       |
| `FEASIBLE`   | 制約は全部満たす解が見つかった（最適かは不明） | 採用       |
| `INFEASIBLE` | **条件が矛盾していて解が存在しない**           | 警告を返す |
| `UNKNOWN`    | 時間内に何も見つからなかった                   | 警告を返す |

```python
if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    for e in emps:
        for d in days:
            for p in pats:
                if solver.Value(x[(e.id, d, p.id)]) == 1:   # 1 になった変数だけ拾う
                    assignments.append({...})
else:
    warnings.append(f"CP-SAT が解を見つけられませんでした ({status_str})。...")
```

2,325 個の変数のうち **1 になったものだけ** を拾い集めれば、それがシフト表です。

`INFEASIBLE` が出る典型例は「必要人員 20 人なのに従業員が 10 人しかいない」など。
そのため `routers/shifts.py` では、ソルバーを呼ぶ **前に** 明らかな矛盾を検査しています。

```python
if len(employees) < max_daily_demand:
    raise HTTPException(status_code=400, detail=(
        f"必要人員 (1 日最大 {max_daily_demand} 名) に対して有効な従業員が "
        f"{len(employees)} 名しかいません。..."
    ))
```

**「20 秒待たされた末に意味不明なエラー」ではなく「即座に理由が分かるエラー」** を返すための配慮です。

---

## 9. 頭脳②：AI による自然文の解釈（`services/llm.py`）

### 9-1. 何のための機能か

管理者が「今月の事情」を自由な日本語で書けるようにする機能です。

> 「8/15 は田中さんが旅行で休み。佐藤さんは試験期間なので週 2 回までにしてほしい。」

このままでは CP-SAT に渡せません。ソルバーが理解できるのは
「従業員 ID 3 は 2026-08-15 に割り当て不可」のような **構造化データ** だけです。
この **翻訳** を LLM（Claude / GPT）にやらせるのがこのファイルです。

### 9-2. プロンプト（AI への指示書）

```python
SYSTEM_PROMPT = """あなたはシフトスケジューリングの制約抽出アシスタントです。
ユーザから与えられる自然言語の「今月の事情」を読み、以下の JSON スキーマに
**厳密に一致する JSON のみ**を出力してください。前後の説明や Markdown は不要です。

スキーマ:
{
  "hard_unavailable": [
    {"employee_id": <int>, "date": "YYYY-MM-DD", "reason": "<string>"}
  ],
  "max_shifts_per_week_override": {
    "<employee_id_as_string>": <int between 0 and 7>
  },
  "date_notes": { "YYYY-MM-DD": "<string>" },
  "warnings": ["<string>"]
}

判断できない情報は空リスト・空オブジェクトとしてください。
日付は必ず YYYY-MM-DD 形式に正規化してください。
"""
```

プロンプト設計のポイントが 3 つあります。

1. **出力形式を厳密に指定** … 「JSON のみ」「説明不要」と念を押す。
   AI は放っておくと「はい、以下が結果です！」などと前置きを付けたがるためです
2. **迷ったら空にしろと指示** … 曖昧な情報を AI が勝手に推測して
   でっち上げる（ハルシネーション）のを防ぎます
3. **日付の正規化を指示** … 「8/15」「来週の金曜」などの表記ゆれを
   `2026-08-15` に統一させます

さらに、AI には **従業員の名前と ID の対応表を一緒に渡します**。

```python
employees_hint = [{"id": e.id, "name": e.name} for e in employees]
```

こうしないと「田中さん」が誰なのか AI には分かりません。

### 9-3. 絶対に落ちない設計

```python
async def derive_constraints_from_text(...) -> dict[str, Any]:
    """Return an object matching the schema. Never raises; returns empty on failure."""

    empty = {"hard_unavailable": [], "max_shifts_per_week_override": {},
             "date_notes": {}, "warnings": []}
    if not note or not note.strip():
        return empty

    try:
        if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
            return await _call_anthropic(...)
        if settings.llm_provider == "openai" and settings.openai_api_key:
            return await _call_openai(...)
    except Exception:
        logger.exception("LLM call failed; falling back to empty constraints")

    empty["warnings"].append(
        "LLM が設定されていない、または呼び出しに失敗したため自然言語制約は無視されました"
    )
    return empty
```

この関数の設計方針は **「Never raises（絶対に例外を投げない）」** です。

外部の AI サービスは、落ちることも、遅いことも、変な返事をすることもあります。
**そのせいでシフト生成全体が失敗してはいけません。**
そこで、何が起きても「制約なし」を返して処理を続行し、
代わりに `warnings` で画面に「AI は使えませんでした」と伝えます。

> **外部サービスに依存する処理は、必ず失敗を想定して書く。**
> このプロジェクトで一番参考になる考え方かもしれません。

`llm_provider` の設定で Anthropic / OpenAI / なし を切り替えられるのも、
**特定の業者に縛られないようにする** ための設計です。

### 9-4. AI の返事の後始末

````python
def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    # trim markdown code fences if present
    if text.startswith("```"):
        text = text.strip("`")
        ...
    return json.loads(text)
````

「JSON だけ返して」と指示しても、AI は ` ```json ... ``` ` のように
**マークダウンのコードブロックで囲んで返してくることがあります**。
そのままでは JSON として読めないので、囲みを剥がしてから解析します。
LLM を扱うコードでは定番の後始末です。

### 9-5. AI の結果をソルバーに渡す

`routers/shifts.py` で両者がつながります。

```python
llm_result = {}
if payload.use_llm and payload.natural_language_note:
    llm_result = await derive_constraints_from_text(...)      # ① AI に翻訳させる

llm_constraints = LLMConstraints(
    hard_unavailable=llm_result.get("hard_unavailable", []) or [],
    max_shifts_per_week_override=llm_result.get("max_shifts_per_week_override", {}) or {},
    date_notes=llm_result.get("date_notes", {}) or {},
)

scheduler = ShiftScheduler(..., llm_constraints=llm_constraints)   # ② ソルバーに渡す
result = scheduler.solve()                                          # ③ 解かせる
```

**AI は「解釈」だけを担当し、実際のシフト作成は CP-SAT が担当する** —
これがこのアプリの設計の要点です。

AI にシフト表そのものを作らせると、
「必要人員が足りない」「同じ人を 1 日に 2 回入れる」といった間違いを平気で起こします。
**曖昧な日本語の解釈は AI が得意、厳密なルール順守は数理ソルバーが得意。**
それぞれの得意分野を分担させています。

---

## 10. 頭脳③：人件費の計算（`services/payroll.py`）

### 10-1. 計算のルール

ファイル冒頭のコメントに前提が明記されています。

```python
"""
  - 割増賃金は「深夜帯 22:00–翌 5:00」を 25% 増しで計算し、人件費に含める
  - 交通費は 1 出勤あたり `employee.transport_cost` 円で計上
  - 保険判定は月間労働時間で行う:
        social:      120h 以上   （社会保険）
        employment:   80–119h    （雇用保険）
        none:         79h 以下   （なし）
"""
```

```
1人あたりの合計 = 基本給(時給 × 総労働時間)
                + 深夜割増(時給 × 深夜時間 × 0.25)
                + 交通費(単価 × 出勤日数)
```

### 10-2. 日をまたぐ勤務の扱い

「17:00 開始 – 01:00 終了」のような夜勤は、終了時刻が開始時刻より小さくなります。
これを素直に引き算すると **マイナス 16 時間** になってしまいます。

```python
def _assignment_intervals(a: ShiftAssignment) -> tuple[datetime, datetime]:
    start = datetime.combine(a.target_date, a.start_time)
    end_date = a.target_date + timedelta(days=1) if a.crosses_midnight else a.target_date
    end = datetime.combine(end_date, a.end_time)
    if end <= start:
        end = end + timedelta(days=1)     # 保険：それでも逆転していたら翌日扱い
    return start, end
```

日付と時刻をくっつけて `datetime` にし、日をまたぐ場合は終了側に 1 日足します。
これで `end - start` が正しく 8 時間になります。

### 10-3. 深夜時間の算出 — このファイルで一番トリッキーな部分

深夜帯は「22:00〜翌 5:00」ですが、**1 日の中では 2 つに分かれます**。

```
0時 ────5時 ────────────────22時 ──24時
 ├─深夜─┤                    ├─深夜─┤
 前夜の続き                    今夜の分
```

コメントでもこの点に注意が促されています。

```python
def _overnight_hours(start: datetime, end: datetime) -> float:
    """Hours worked within the 22:00–翌 5:00 overnight band.

    Within any calendar day the band splits into two sub-windows: ...
    considering only ``[22:00, tomorrow 05:00)`` would miss early-morning
    hours such as a 01:00–09:00 shift.
    """
    total = 0.0
    cursor = start
    while cursor < end:
        day = cursor.date()
        day_end = datetime.combine(day + timedelta(days=1), time.min)
        chunk_end = min(end, day_end)
        windows = (
            (datetime.combine(day, time.min), datetime.combine(day, OVERNIGHT_END)),    # 00:00-05:00
            (datetime.combine(day, OVERNIGHT_START), day_end),                          # 22:00-24:00
        )
        for w_start, w_end in windows:
            seg_start = max(cursor, w_start)      # 重なりの開始
            seg_end = min(chunk_end, w_end)       # 重なりの終了
            if seg_start < seg_end:               # 重なっていれば
                total += (seg_end - seg_start).total_seconds() / 3600.0
        cursor = day_end
    return total
```

やっていることは **「勤務時間と深夜帯の重なりを日ごとに測って足す」** だけです。
`max(開始同士)` と `min(終了同士)` を取り、
前者が後者より小さければ重なりあり — 区間の重なりを求める定番の計算です。

もし「22:00〜翌 5:00」を 1 つの塊としてだけ考えると、
**「深夜 01:00–09:00」のシフトの 01:00–05:00 部分（4 時間）を数え落とします。**
コメントはまさにその落とし穴を警告しています。

そしてこの挙動は、テストで守られています。

```python
def test_calculate_payroll_night_shift_with_premium():
    # 深夜 01:00–09:00: 01:00-05:00 の 4h が深夜帯
    a = _make_assignment(1, "2025-06-02", "01:00", "09:00")
    report = calculate_payroll(2025, 6, [a], {1: emp})
    assert report.rows[0].overnight_hours == 4.0
```

### 10-4. 集計とレポート

```python
rows.append(PayrollRow(
    employee_id=emp.id,
    employee_name=emp.name,
    total_hours=round(total_hours, 2),
    overnight_hours=round(overnight_hours, 2),
    base_wage=base_wage,
    overnight_premium=overnight_premium,
    transport_cost_total=transport_cost_total,
    insurance_status=insurance,
    grand_total=grand,
))
```

**従業員別（`rows`）** と **日別（`per_day`）** の 2 つの切り口で集計し、
月間合計（`monthly_total`）と一緒に返します。
これがフロントの人件費画面で 2 つの表として表示されます。

> ファイル冒頭の `TODO (先方確認事項)` に、
> 「有給の計上ルール」「交通費の月上限」「社会保険の会社負担分を含めるか」が
> **未確定事項として明記されています**。
> 仕様が決まっていない部分をコードに書き残しておくのは良い習慣です。

---

## 11. ファイル出力（`services/export.py`）

シフト表を PDF と Excel に変換します。両者で **表の中身を作る部分は共通** です。

```python
def _build_grid(year, month, assignments, employees) -> tuple[list[date], list[list[str]]]:
    _, ndays = calendar.monthrange(year, month)        # その月の日数
    days = [date(year, month, d) for d in range(1, ndays + 1)]

    per_emp_day = defaultdict(lambda: defaultdict(list))
    for a in assignments:
        per_emp_day[a.employee_id][a.target_date].append(a.shift_type)

    header = ["従業員"] + [f"{d.day}({'月火水木金土日'[d.weekday()]})" for d in days]
    rows = [header]
    for e in employees:
        row = [e.name]
        for d in days:
            row.append("/".join(per_emp_day[e.id].get(d, [])) or "-")   # 無ければ "-"
        rows.append(row)
    return days, rows
```

「割り当てのリスト」を「従業員 × 日付」のマス目に組み替えています。
フロントの `ShiftTableView.vue` が `v-for` の二重ループでやっていることと **同じ変形** です。

`'月火水木金土日'[d.weekday()]` は、曜日番号（0=月）で文字列から 1 文字取り出す小技です。

**PDF（reportlab）**

```python
def _register_jp_font() -> str:
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
        return "HeiseiKakuGo-W5"
    except Exception:
        return "Helvetica"
```

PDF は標準では日本語が出せず **文字化けします**。日本語フォントの登録が必須です。
失敗しても落ちないよう、`Helvetica` にフォールバックします。

```python
for i, d in enumerate(days, start=1):
    if d.weekday() == 5:
        style.add("TEXTCOLOR", (i, 0), (i, 0), colors.blue)     # 土曜は青
    elif d.weekday() == 6 or is_holiday(d):
        style.add("TEXTCOLOR", (i, 0), (i, 0), colors.red)      # 日祝は赤
```

土曜を青、日曜・祝日を赤にする、カレンダーの慣習どおりの色分けです。
Excel 側でも同じことを背景色（`PatternFill`）でやっています。

**返し方（`routers/shifts.py`）**

```python
pdf = export_pdf(shift.year, shift.month, list(shift.assignments), employees)
return Response(
    content=pdf,
    media_type="application/pdf",
    headers={"Content-Disposition": f'attachment; filename="shift-{shift.year}-{shift.month:02d}.pdf"'},
)
```

- `media_type` … 「これは PDF ファイルです」とブラウザに伝える
- `Content-Disposition: attachment` … 「表示ではなくダウンロードして」の指示
- `filename=...` … 保存されるファイル名

生成された PDF は **ファイルとして保存せず、メモリ上（`io.BytesIO`）で作って直接返します**。
サーバーにゴミファイルが溜まりません。

---

## 12. データベースの変更履歴（`alembic/`）

開発中は「従業員に新しい項目を足したい」ということが頻繁に起きます。
しかし **すでにデータが入っている本番の DB を作り直すわけにはいきません**。

そこで **Alembic**（アレンビック）で、DB の設計変更を
**Git のコミットのように 1 個ずつ記録** します。

```
alembic/versions/
└── 0001_initial.py      ← 最初のテーブル一式を作る変更
```

各ファイルには「適用する（`upgrade`）」と「取り消す（`downgrade`）」が書かれており、
`alembic upgrade head` を実行すると **未適用の変更だけ** が順に適用されます。
どの環境（自分の PC・検証・本番）でも **同じ手順で同じ構造の DB になる** のが利点です。

---

## 13. 開発用の便利機能（`routers/dev.py`）

動作確認のたびに従業員を手で 25 人登録するのは大変なので、
**テストデータを一発で投入する窓口** が用意されています。

```python
def _require_dev() -> None:
    if settings.environment != "development":
        raise HTTPException(status_code=404, detail="dev endpoints disabled")
```

**必ず最初に環境をチェックします。** 本番環境ではこの窓口自体が存在しないかのように
`404` を返します（「あるけど使えません」だと窓口の存在自体がバレるため、
`403` ではなく `404` を返しています）。

```python
@router.post("/seed")
def seed(db: ...):
    _require_dev()

    if not db.execute(select(ShiftPattern)).first():     # ← 既にあれば作らない
        db.add_all([ShiftPattern(code="morning", ...), ...])

    if not db.execute(select(StaffingRule)).first():
        db.add_all([StaffingRule(day_category=DayCategory.weekday, ...), ...])

    if not db.execute(select(Employee)).first():
        db.add_all([
            Employee(
                name=f"従業員{i:02d}",
                hourly_wage=1200,
                main_shift_type=["morning", "evening", "night"][i % 3],
                weekly_shifts=3 + (i % 3),
            )
            for i in range(1, 26)                        # 25 人分
        ])
    db.commit()
    return {"status": "seeded"}
```

`if not ...first():` で **既にデータがあれば何もしません**。
何度実行しても結果が同じになる性質を **冪等性（べきとうせい）** といい、
セットアップ処理では重要な性質です。

`/reset` は全部消してから `seed()` を呼び直します（データがおかしくなったとき用）。

---

## 14. テスト（`tests/`）

```python
def test_calculate_payroll_basic_shift():
    emp = _make_employee(1, "田中")
    a = _make_assignment(1, "2025-06-02", "09:00", "17:00")
    report = calculate_payroll(2025, 6, [a], {1: emp})
    row = report.rows[0]
    assert row.total_hours == 8.0
    assert row.base_wage == 8 * 1200
```

`assert`（アサート）は **「これが成り立つはず」という確認** です。
成り立たなければテストが失敗し、どこが壊れたかすぐ分かります。

注目したいのは、DB もサーバーも起動せずにテストできている点です。

```python
def _make_employee(id_, name, hourly_wage=1200, transport=500):
    return SimpleNamespace(id=id_, name=name, hourly_wage=hourly_wage, transport_cost=transport)
```

`SimpleNamespace` は **「必要な属性だけ持った偽物のオブジェクト」** を作る道具です。
`calculate_payroll` は `emp.hourly_wage` などしか触らないので、
本物の `Employee`（＝DB 接続が必要）でなくても動きます。

これが第 2 章で触れた **「計算を `services` に分けておく」設計の効果** です。
窓口の中に計算を書いていたら、テストのたびに DB とサーバーの起動が必要でした。

```bash
cd backend && pytest
```

---

## 15. まとめ：1 つの操作を最初から最後まで追う

**「シフト表画面で AI 生成ボタンを押す」** とき、バックエンドで何が起きるかを追います。

```
① 画面から POST /api/shifts/generate が届く
   body: { year: 2026, month: 8, natural_language_note: "8/15は田中さん休み", use_llm: true }
      │
② FastAPI が ShiftGenerateRequest スキーマで検証
   （month が 1-12 か等。おかしければ即 422 を返して終了）
      │
③ AdminUser の依存が発動 → トークン検証 → 管理者か確認
   （ダメなら 401 / 403 を返して終了。関数は呼ばれない）
      │
④ generate_shift() 開始。DB から材料を集める
   ・有効な従業員一覧      ・シフトパターン（なければ既定値を自動作成）
   ・必要人員ルール        ・休み希望／出勤希望
      │
⑤ 事前チェック：従業員数 < 1日の必要人員 なら 400 で即エラー
      │
⑥ services/llm.py → AI が自然文を構造化制約に翻訳
   "8/15は田中さん休み" → {"hard_unavailable": [{"employee_id": 3, "date": "2026-08-15"}]}
   （AI が失敗しても空の制約で続行）
      │
⑦ services/scheduler.py → CP-SAT に投入
   ・変数 2,325 個を作る
   ・ハード制約（1日1シフト / 休み希望 / 必要人員ぴったり）
   ・ソフト制約（週の回数・希望日・メインシフト）を点数化
   ・最大 20 秒で解を探す
      │
⑧ 解を ShiftAssignment のリストに変換
      │
⑨ DB に保存（既存の割り当てを消してから入れ直し → commit）
      │
⑩ ShiftGenerateResult を JSON で返す
   { shift_id, assignments: [...], solver_status: "OPTIMAL",
     solver_seconds: 3.2, warnings: [] }
      │
⑪ 画面が受け取り、Pinia ストアを更新 → 表が自動で書き換わる
```

この流れの中に、本ドキュメントで説明した要素がすべて登場します。

| 要素                  | 役割                     | 出てきた章 |
| --------------------- | ------------------------ | ---------- |
| router                | 窓口。材料集めと結果返却 | 7          |
| schema（Pydantic）    | 入出力の検証と整形       | 5          |
| Depends / CurrentUser | ログイン・権限の関所     | 6          |
| model（SQLAlchemy）   | DB の表とのやり取り      | 4          |
| services/llm          | 自然文 → 構造化制約      | 9          |
| services/scheduler    | CP-SAT でシフト生成      | 8          |
| services/payroll      | 人件費の計算             | 10         |
| services/export       | PDF / Excel 出力         | 11         |

---

## 16. フロントエンドとの対応表

| やりたいこと       | フロント側                                     | バック側                                     |
| ------------------ | ---------------------------------------------- | -------------------------------------------- |
| 従業員一覧を出す   | `stores/employee.ts` → `api.get('/employees')` | `routers/employees.py` の `list_employees`   |
| 従業員を追加する   | `EmployeesView.vue` → `store.create()`         | `routers/employees.py` の `create_employee`  |
| シフトを生成する   | `ShiftTableView.vue` → `shiftStore.generate()` | `routers/shifts.py` の `generate_shift`      |
| 人件費を見る       | `PayrollView.vue` → `fetchPayroll()`           | `routers/payroll.py` → `services/payroll.py` |
| PDF を落とす       | `PrintPreviewView.vue` の `download()`         | `routers/shifts.py` の `export_shift_pdf`    |
| データの形の定義   | `types/index.ts`（TypeScript）                 | `schemas/*.py`（Pydantic）                   |
| ログイン状態の保持 | `stores/auth.ts`（localStorage）               | `core/security.py`（JWT 発行・検証）         |

**`types/index.ts` と `schemas/` は、同じデータを両側から定義したもの** です。
片方を変えたらもう片方も直す必要があります。

---

## 付録：用語ミニ辞典

| 用語                  | かんたんな意味                                  |
| --------------------- | ----------------------------------------------- |
| API                   | サーバーが提供する「お願いの窓口」              |
| エンドポイント        | 窓口 1 個。URL とメソッドの組み合わせ           |
| FastAPI               | Python で API を作るライブラリ                  |
| デコレータ            | `@router.get(...)` のような、関数に付ける飾り   |
| ルーター              | 窓口をグループにまとめたもの                    |
| CORS                  | 別アドレスの画面からの通信を許可する設定        |
| ORM                   | DB の表を Python のクラスとして扱う仕組み       |
| SQLAlchemy            | このプロジェクトで使っている ORM                |
| モデル                | DB の表の設計図（`models/`）                    |
| スキーマ              | やり取りする JSON の設計図（`schemas/`）        |
| Pydantic              | スキーマ定義と入力検証のライブラリ              |
| マイグレーション      | DB の設計変更を記録して適用すること（Alembic）  |
| セッション            | DB との 1 回分のやり取り                        |
| コミット              | DB への変更を確定させること                     |
| 外部キー              | 「この列は別の表の ID です」という関連付け      |
| Depends               | 「処理の前にこれを実行して」という依存性注入    |
| JWT                   | 署名付きの通行証。ログイン状態の証明            |
| OAuth 2.0             | 「Google でログイン」を実現する標準手順         |
| 401 / 403 / 404 / 422 | 未認証 / 権限なし / 見つからない / 入力不正     |
| CP-SAT                | 制約を満たす答えを探す Google 製のソルバー      |
| ハード制約            | 絶対に守るルール                                |
| ソフト制約            | できれば守りたい希望（点数で表現）              |
| 目的関数              | 「何を最小化／最大化したいか」の式              |
| LLM                   | 大規模言語モデル。Claude や GPT のこと          |
| プロンプト            | AI への指示文                                   |
| 冪等性                | 何度実行しても結果が同じになる性質              |
| `async` / `await`     | 「時間のかかる処理を待つ」ための書き方          |
| `yield`               | 途中で一旦値を渡し、後で処理を再開する `return` |

---

_このドキュメントは `backend/app` 以下のソースコードをもとに作成した解説資料です。_
