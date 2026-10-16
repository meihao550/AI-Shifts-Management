"""本番スクリプト共通の小ヘルパー（seed_prod / teardown_prod で共有）。"""

from urllib.parse import urlsplit

from app.core.config import get_settings


def db_host() -> str:
    """接続先DBのホスト名を返す（パスワードは出さない）。実行前の接続先確認に使う。"""
    try:
        url = get_settings().database_url.replace("postgresql+psycopg", "postgresql")
        return urlsplit(url).hostname or "?"
    except Exception:
        return "?"
