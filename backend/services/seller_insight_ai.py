import json
import os

from backend.services.seller_insight_fallback import build_fallback_insight
from backend.services.seller_insight_schema import (
    SELLER_INSIGHT_JSON_SCHEMA,
    build_insight_payload,
)

DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_TIMEOUT_SECONDS = 8

SYSTEM_PROMPT = """
你是一名电商卖家运营分析师。你会基于结构化店铺指标，输出简洁、可执行、面向卖家的中文运营洞察。
规则：
1. 不要编造指标、商品或订单状态。
2. 每张行动卡必须引用输入中已有的数字证据。
3. 优先给出具体动作，例如补货、处理待发货订单、优化滞销品，而不是泛泛建议。
4. 输出必须符合 JSON schema。
""".strip()


def _extract_output_text(response):
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text
    if isinstance(response, dict):
        if response.get("output_text"):
            return response["output_text"]
        for item in response.get("output") or []:
            for content in item.get("content", []):
                if content.get("text"):
                    return content["text"]
    raise ValueError("OpenAI response did not include output text")


def _parse_model_payload(raw_text):
    parsed = json.loads(raw_text)
    briefing = parsed.get("briefing")
    cards = parsed.get("cards")
    if not briefing or not isinstance(cards, list) or not cards:
        raise ValueError("OpenAI response did not match seller insight shape")
    return briefing, cards


def _create_openai_client(api_key, timeout_seconds):
    from openai import OpenAI
    return OpenAI(api_key=api_key, timeout=timeout_seconds)


def generate_seller_insight(metrics, client=None):
    fallback_payload = build_fallback_insight(metrics)
    api_key = os.environ.get("OPENAI_API_KEY")
    if client is None and not api_key:
        return fallback_payload

    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    try:
        timeout_seconds = float(os.environ.get("OPENAI_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
    except ValueError:
        timeout_seconds = DEFAULT_TIMEOUT_SECONDS

    try:
        if client is None:
            client = _create_openai_client(api_key, timeout_seconds)
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({"metrics": metrics}, ensure_ascii=False)}
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "seller_insight_response",
                    "schema": SELLER_INSIGHT_JSON_SCHEMA,
                    "strict": True
                }
            }
        )
        briefing, cards = _parse_model_payload(_extract_output_text(response))
        return build_insight_payload(briefing, cards, metrics, "openai")
    except Exception:
        return fallback_payload
