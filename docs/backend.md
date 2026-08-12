# エントリーポイント(最初に読み込まれるファイル)

backend/app/main.py これがエントリーポイントのファイルです。

### ファイルの説明文章

`"""FastAPI application entrypoint."""`

- 一行目にあるこのソースコードは、python標準の文法で、ファイルの一番上においた文字列は、そのファイルの説明として扱われるただの文字列です

---

### モジュールやパッケージの読み込み

```
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import auth, dev, employees, payroll, rules, shifts
```

- `from fastapi import FastAPI` このソースコードはここを参照: [FastAPI](https://fastapi.tiangolo.com/ja/reference/fastapi/)

---

### envファイルの読み込み

`settings = get_settings()`

- envファイルを読み込みます

---

### FastAPIの読み込み

```
app = FastAPI(
    title="AI-Shifts-Management API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
```

- このソースコードはここを参照: [FastAPI](https://fastapi.tiangolo.com/ja/reference/fastapi/)

---

### CORSを許可するための設定

```
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- CORSについて簡単な解説→CORSとは、**別の場所(origin)にあるWebサイトからのアクセスを許可する仕組みのこと** です。
- CORS,ソースコードの詳細な解説はここを参照: [CORS](https://fastapi.tiangolo.com/ja/tutorial/cors)

---

### サーバーが正常に動いているか確認するためのAPI

```
@app.get("/api/health", tags=["Health Check"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
```

- <dt>1行目の処理</dt>
      <dd>/api/health にgetリクエストが来たら、下の health() を実行する</dd>
- <dt>2行目の処理</dt>
    <dd>関数の戻り値の型を指定している今回は、キーと値がどちらも文字列(str)の辞書(dict)を返す</dd>
- <dt>3行目の処理</dt>
      <dd>クライアントに、サーバーの状態(ok)と実行環境の情報を返す。</dd>
- このソースコードについての補足はここを参照: [tutorial](https://fastapi.tiangolo.com/ja/tutorial/first-steps/)

---

### 別のファイルに分けて作ったAPIを、メインのFastAPIアプリに追加する

```
app.include_router(auth.router, prefix="/api")
app.include_router(employees.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(shifts.router, prefix="/api")
app.include_router(payroll.router, prefix="/api")
app.include_router(dev.router, prefix="/api")
```

- app.include_router(...)は**このAPIもアプリで使えるようにしてください**という命令をしています。
  &emsp; 例: app.include_router(auth.router)なら,authに作ってあるAPIをアプリに追加しています。
- prefix="/api"は**URLの最初に/apiをつける**動作をしています。/apiをつけることにより、API用のURLであることが分かりやすくなり、管理も行いやすくなります。
