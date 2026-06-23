from backend.services.seller_insight_knowledge import load_seller_ops_knowledge

TAG_PRIORITY = [
    "pending_orders",
    "low_stock",
    "slow_moving",
    "revenue_concentration",
    "promotion",
]

TAG_KEYWORDS = {
    "pending_orders": ["待发货", "履约", "pending", "发货"],
    "low_stock": ["低库存", "补货", "库存", "安全库存"],
    "slow_moving": ["滞销", "促活", "库存高", "销量为 0"],
    "revenue_concentration": ["收入集中", "核心商品", "第二增长点"],
    "promotion": ["促销", "组合销售", "热销", "折扣"],
}


def infer_query_tags(metrics):
    tags = []
    if int(metrics.get("pendingOrders") or 0) > 0:
        tags.append("pending_orders")
    if metrics.get("lowStockProducts") or []:
        tags.append("low_stock")
    if metrics.get("slowMovingProducts") or []:
        tags.append("slow_moving")
    if float(metrics.get("revenueConcentration") or 0) >= 0.7:
        tags.append("revenue_concentration")
    if (metrics.get("topProducts") or []) or (metrics.get("slowMovingProducts") or []):
        tags.append("promotion")
    return tags


def _keyword_score(document, tag):
    text = f"{document.get('title', '')}\n{document.get('content', '')}".lower()
    return sum(1 for keyword in TAG_KEYWORDS.get(tag, []) if keyword.lower() in text)


def _score_document(document, tags):
    score = 0
    topic = document.get("topic")
    for index, tag in enumerate(tags):
        if topic == tag:
            score += 100 - index
        score += _keyword_score(document, tag)
    return score


def _snippet_from_document(document, score):
    content = str(document.get("content") or "")
    return {
        "id": str(document.get("id") or ""),
        "title": str(document.get("title") or "运营知识"),
        "topic": str(document.get("topic") or "general"),
        "content": content[:1200],
        "sourcePath": str(document.get("sourcePath") or ""),
        "score": score,
    }


def retrieve_seller_insight_knowledge(metrics, documents=None, max_snippets=3):
    tags = infer_query_tags(metrics)
    if not tags:
        return []

    knowledge_documents = documents if documents is not None else load_seller_ops_knowledge()
    scored = []
    for document in knowledge_documents:
        score = _score_document(document, tags)
        if score > 0:
            scored.append((score, document))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        _snippet_from_document(document, score)
        for score, document in scored[:max_snippets]
    ]
