"""LLM integration — converts a natural-language monthly note into structured constraints.

Supports Anthropic Claude and OpenAI. Selected via `LLM_PROVIDER`.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

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
  "date_notes": {
    "YYYY-MM-DD": "<string>"
  },
  "warnings": ["<string>"]
}

判断できない情報は空リスト・空オブジェクトとしてください。
日付は必ず YYYY-MM-DD 形式に正規化してください。
"""


async def derive_constraints_from_text(
    note: str,
    employees_hint: list[dict[str, Any]],
    year: int,
    month: int,
) -> dict[str, Any]:
    """Return an object matching the schema. Never raises; returns empty on failure."""

    settings = get_settings()
    empty: dict[str, Any] = {
        "hard_unavailable": [],
        "max_shifts_per_week_override": {},
        "date_notes": {},
        "warnings": [],
    }
    if not note or not note.strip():
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
        if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
            return await _call_anthropic(user_prompt, settings.anthropic_api_key, settings.anthropic_model)
        if settings.llm_provider == "openai" and settings.openai_api_key:
            return await _call_openai(user_prompt, settings.openai_api_key, settings.openai_model)
    except Exception:
        logger.exception("LLM call failed; falling back to empty constraints")

    empty["warnings"].append(
        "LLM が設定されていない、または呼び出しに失敗したため自然言語制約は無視されました"
    )
    return empty


async def _call_anthropic(user_prompt: str, api_key: str, model: str) -> dict[str, Any]:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=api_key)
    message = await client.messages.create(
        model=model,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(block.text for block in message.content if getattr(block, "type", "") == "text")
    return _parse_json(text)


async def _call_openai(user_prompt: str, api_key: str, model: str) -> dict[str, Any]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    resp = await client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return _parse_json(resp.choices[0].message.content or "{}")


def _parse_json(text: str) -> dict[str, Any]:
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
