import json
import os

from backend.services.seller_insight_fallback import build_fallback_insight
from backend.services.seller_insight_schema import (
    SELLER_INSIGHT_JSON_SCHEMA,
    build_insight_payload,
)

DEFAULT_BASE_URL = "https://openrouter.fans/v1"
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_TIMEOUT_SECONDS = 8
PROVIDER_SOURCE = "deepseek"

SYSTEM_PROMPT = """
你是一名电商卖家运营分析师。你会基于结构化店铺指标，输出简洁、可执行、面向卖家的中文运营洞察。
规则：
1. 不要编造指标、商品或订单状态。
2. 每张行动卡必须引用输入中已有的数字证据。
3. 优先给出具体动作，例如补货、处理待发货订单、优化滞销品，而不是泛泛建议。
4. 只输出 JSON 对象，不要输出 Markdown 或解释文字。
5. JSON 对象必须只包含 briefing 和 cards 字段，并符合请求中的 schema。
""".strip()


def _extract_output_text(response):
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text

    choices = getattr(response, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if content:
            return content

    if isinstance(response, dict):
        if response.get("output_text"):
            return response["output_text"]
        for choice in response.get("choices") or []:
            message = choice.get("message") or {}
            if message.get("content"):
                return message["content"]
        for item in response.get("output") or []:
            for content in item.get("content", []):
                if content.get("text"):
                    return content["text"]
    raise ValueError("DeepSeek response did not include output text")


def _parse_model_payload(raw_text):
    parsed = json.loads(raw_text)
    briefing = parsed.get("briefing")
    cards = parsed.get("cards")
    if not briefing or not isinstance(cards, list) or not cards:
        raise ValueError("DeepSeek response did not match seller insight shape")
    return briefing, cards


def _create_deepseek_client(api_key, base_url, timeout_seconds):
    from openai import OpenAI
    return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds, max_retries=0)


def _timeout_seconds():
    try:
        return float(os.environ.get("DEEPSEEK_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def _user_prompt(metrics):
    return json.dumps({
        "metrics": metrics,
        "requiredOutputSchema": SELLER_INSIGHT_JSON_SCHEMA,
    }, ensure_ascii=False)


def generate_seller_insight(metrics, client=None):
    fallback_payload = build_fallback_insight(metrics)
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if client is None and not api_key:
        return fallback_payload

    model = os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL)
    base_url = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)

    try:
        if client is None:
            client = _create_deepseek_client(api_key, base_url, _timeout_seconds())
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(metrics)}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        briefing, cards = _parse_model_payload(_extract_output_text(response))
        return build_insight_payload(briefing, cards, metrics, PROVIDER_SOURCE)
    except Exception:
        return fallback_payload
