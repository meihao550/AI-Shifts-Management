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
