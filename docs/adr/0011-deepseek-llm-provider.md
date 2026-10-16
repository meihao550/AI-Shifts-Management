# 自然言語制約抽出の LLM プロバイダに DeepSeek を追加

シフト生成では「今月の事情」を自然言語で入力でき、LLM が JSON 制約（全員休み・個別勤務不可・週回数上限など）に変換する（`backend/app/services/llm.py`）。従来は Anthropic / OpenAI のみ対応だったが、安価に運用するため **DeepSeek** を選択肢に追加する。

DeepSeek API は **OpenAI 互換**のため、既存の `_call_openai` を `base_url` 対応に一般化し、`LLM_PROVIDER=deepseek` のとき `base_url=https://api.deepseek.com` / `model=deepseek-chat` で同じ経路を使う。設定は `Settings`（`deepseek_api_key` / `deepseek_model` / `deepseek_base_url`）に追加。外部 API ハング対策として `timeout=20s` / `max_retries=0` を明示し、失敗時は空制約＋警告にフォールバックする（生成は止めない）。

本番は Secret Manager に `deepseek-api-key` を置き、Cloud Run に `LLM_PROVIDER=deepseek` を設定して有効化する（terraform にも反映）。無効化したい月は `LLM_PROVIDER=none` に戻すだけでトークン課金は発生しない。

## Considered Options

- **Anthropic / OpenAI のみ**（却下）: 既存対応だが、本件はコスト最優先で DeepSeek を使いたい。
- **DeepSeek 専用クライアントを別実装**（却下）: OpenAI 互換なので `base_url` 差し替えで足り、重複になる。
- **LLM 呼び出しに timeout を付けない**（却下）: Cloud Run の 300 秒上限内で外部 API がハングし、生成全体が巻き込まれるため不可。
