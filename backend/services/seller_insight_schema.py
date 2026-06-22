from datetime import datetime

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
VALID_PRIORITIES = set(PRIORITY_ORDER)

SELLER_INSIGHT_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["briefing", "cards"],
    "properties": {
        "briefing": {"type": "string"},
        "cards": {
            "type": "array",
            "minItems": 1,
            "maxItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "priority", "recommendation", "reason", "evidence", "metric"],
                "properties": {
                    "title": {"type": "string"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                    "recommendation": {"type": "string"},
                    "reason": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 4
                    },
                    "metric": {"type": "string"}
                }
            }
        }
    }
}


def utc_now_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def normalize_priority(priority):
    value = str(priority or "medium").lower()
    return value if value in VALID_PRIORITIES else "medium"


def normalize_evidence(evidence):
    if isinstance(evidence, list):
        values = [str(item) for item in evidence if str(item).strip()]
    elif evidence:
        values = [str(evidence)]
    else:
        values = []
    return values[:4] or ["暂无可用指标"]


def normalize_card(card):
    card = card or {}
    return {
        "title": str(card.get("title") or "运营建议"),
        "priority": normalize_priority(card.get("priority")),
        "recommendation": str(card.get("recommendation") or "继续观察店铺数据，保持当前运营节奏。"),
        "reason": str(card.get("reason") or "当前数据不足以形成更具体的判断。"),
        "evidence": normalize_evidence(card.get("evidence")),
        "metric": str(card.get("metric") or "general")
    }


def normalize_cards(cards):
    if not isinstance(cards, list):
        cards = []
    normalized = [normalize_card(card) for card in cards]
    normalized.sort(key=lambda item: PRIORITY_ORDER.get(item["priority"], 1))
    return normalized[:5]


def build_insight_payload(briefing, cards, metrics, source):
    normalized_cards = normalize_cards(cards)
    if not normalized_cards:
        normalized_cards = [normalize_card({})]
    window_days = int(metrics.get("windowDays", 30) or 30)
    return {
        "briefing": str(briefing or "暂无足够数据生成运营简报。"),
        "cards": normalized_cards,
        "metrics": metrics,
        "meta": {
            "source": source,
            "generatedAt": utc_now_iso(),
            "windowDays": window_days
        }
    }
