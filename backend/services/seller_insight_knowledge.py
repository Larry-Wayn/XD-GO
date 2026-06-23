from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge" / "seller_ops"

DOCUMENT_TOPICS = {
    "inventory_restocking": "low_stock",
    "slow_moving_products": "slow_moving",
    "fulfillment_risk": "pending_orders",
    "revenue_concentration": "revenue_concentration",
    "promotion_playbook": "promotion",
}


def _title_from_markdown(content, fallback):
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or fallback
    return fallback


def _document_id(path):
    return path.stem


def _topic_for_document(document_id):
    return DOCUMENT_TOPICS.get(document_id, "general")


def source_from_document(document):
    return {
        "id": str(document.get("id") or ""),
        "title": str(document.get("title") or "运营知识"),
        "topic": str(document.get("topic") or "general"),
    }


def load_seller_ops_knowledge(knowledge_dir=None):
    base_dir = Path(knowledge_dir) if knowledge_dir else KNOWLEDGE_DIR
    if not base_dir.exists() or not base_dir.is_dir():
        return []

    documents = []
    for path in sorted(base_dir.glob("*.md")):
        try:
            content = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not content:
            continue

        document_id = _document_id(path)
        documents.append({
            "id": document_id,
            "title": _title_from_markdown(content, document_id),
            "topic": _topic_for_document(document_id),
            "content": content,
            "sourcePath": str(path),
        })

    return documents
