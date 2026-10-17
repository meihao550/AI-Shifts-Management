"""LLM 連携：自然言語の「今月の事情」→ 構造化された制約(JSON)。

プロバイダ(anthropic / openai / deepseek)は **戦略(Strategy)** として差し替え可能にしてある。
新しいプロバイダを足すときは `resolve_provider` に分岐を1つ追加するだけでよい（開放/閉鎖原則 OCP）。
DeepSeek は OpenAI 互換 API のため、`OpenAICompatProvider` を base_url 違いで共用する。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# 外部APIがハングして生成リクエスト全体(Cloud Run 300秒上限)を巻き込まないための共通設定。
_TIMEOUT_SECONDS = 20.0
_MAX_RETRIES = 0
# 未設定/失敗時に制約を無視したことを知らせる警告文（複数箇所で同一文言を使う）。
_FALLBACK_WARNING = (
    "LLM が設定されていない、または呼び出しに失敗したため自然言語制約は無視されました"
)

SYSTEM_PROMPT = """あなたはシフトスケジューリングの制約抽出アシスタントです。
ユーザから与えられる自然言語の「今月の事情」を読み、以下の JSON スキーマに
**厳密に一致する JSON のみ**を出力してください。前後の説明や Markdown は不要です。

スキーマ:
{
  "closed_dates": ["YYYY-MM-DD"],
  "hard_unavailable": [
    {"employee_id": <int>, "date": "YYYY-MM-DD", "reason": "<string>"}
  ],
  "max_shifts_per_week_override": {
    "<employee_id_as_string>": <int between 0 and 7>
  },
  "date_notes": {
    "YYYY-MM-DD": "<string>"
  },
  "warnings": ["<string>"]
}

重要:
- 「全員休み」「休業」「定休日」など"全従業員がその日は勤務しない"指示は、個別の
  hard_unavailable に展開せず closed_dates にその日付を入れてください（ハード制約で誰も配置されません）。
- 特定の従業員だけが勤務不可の場合のみ hard_unavailable を使います。
- 判断できない情報は空リスト・空オブジェクトとしてください。
- 日付は必ず YYYY-MM-DD 形式に正規化してください。
"""


class LlmProvider(Protocol):
    """1回の LLM 呼び出し戦略。system/user プロンプトを渡し、生の応答テキストを返す。"""

    async def complete(self, system: str, user: str) -> str:
        """system/user プロンプトを LLM に送り、生の応答テキストを返す。"""
        ...


class AnthropicProvider:
    """Anthropic Claude を呼ぶプロバイダ。"""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def complete(self, system: str, user: str) -> str:
        """Claude にプロンプトを投げ、テキストブロックを連結して返す。"""
        import anthropic

        client = anthropic.AsyncAnthropic(
            api_key=self._api_key, timeout=_TIMEOUT_SECONDS, max_retries=_MAX_RETRIES
        )
        message = await client.messages.create(
            model=self._model,
            max_tokens=1500,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )


class OpenAICompatProvider:
    """OpenAI 互換 API を呼ぶプロバイダ。base_url を変えれば DeepSeek 等にも向く。"""

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    async def complete(self, system: str, user: str) -> str:
        """chat.completions に JSON 強制で投げ、本文テキストを返す。"""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=_TIMEOUT_SECONDS,
            max_retries=_MAX_RETRIES,
        )
        resp = await client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or "{}"


def resolve_provider(settings: Settings) -> LlmProvider | None:
    """設定(LLM_PROVIDER＋対応するAPIキー)から使うプロバイダを1つ返す。無効なら None。

    新しいプロバイダはここに分岐を1つ追加するだけで対応できる（OCP）。
    """
    provider = settings.llm_provider
    if provider == "anthropic" and settings.anthropic_api_key:
        return AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model)
    if provider == "openai" and settings.openai_api_key:
        return OpenAICompatProvider(settings.openai_api_key, settings.openai_model)
    if provider == "deepseek" and settings.deepseek_api_key:
        # DeepSeek は OpenAI 互換。base_url を差し替えるだけで同じ呼び出し経路を使う。
        return OpenAICompatProvider(
            settings.deepseek_api_key, settings.deepseek_model, settings.deepseek_base_url
        )
    return None


def _empty_result() -> dict[str, Any]:
    """スキーマに一致する空の制約オブジェクトを返す。"""
    return {
        "closed_dates": [],
        "hard_unavailable": [],
        "max_shifts_per_week_override": {},
        "date_notes": {},
        "warnings": [],
    }


async def derive_constraints_from_text(
    note: str,
    employees_hint: list[dict[str, Any]],
    year: int,
    month: int,
) -> dict[str, Any]:
    """自然言語メモをスキーマ準拠の JSON 制約へ変換する。

    例外は投げず、プロバイダ未設定や呼び出し失敗のときは空の制約＋警告を返す
    （生成処理は止めない）。
    """
    empty = _empty_result()
    if not note or not note.strip():
        return empty

    provider = resolve_provider(get_settings())
    if provider is None:
        empty["warnings"].append(_FALLBACK_WARNING)
        return empty

    user_prompt = json.dumps(
        {
            "target_year": year,
            "target_month": month,
            "employees": employees_hint,
            "note": note,
        },
        ensure_ascii=False,
    )
    try:
        return _parse_json(await provider.complete(SYSTEM_PROMPT, user_prompt))
    except Exception:
        logger.exception("LLM call failed; falling back to empty constraints")
        empty["warnings"].append(_FALLBACK_WARNING)
        return empty


def _parse_json(text: str) -> dict[str, Any]:
    """LLM 応答テキストを JSON として読み込む（```コードフェンスが付いていれば除去）。"""
    text = text.strip()
    # trim markdown code fences if present
    if text.startswith("```"):
        text = text.strip("`")
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return json.loads(text)
