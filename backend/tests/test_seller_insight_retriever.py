from backend.services.seller_insight_retriever import (
    infer_query_tags,
    retrieve_seller_insight_knowledge,
)


DOCUMENTS = [
    {
        "id": "inventory_restocking",
        "title": "库存补货策略",
        "topic": "low_stock",
        "content": "低库存商品需要确认库存和补货。",
        "sourcePath": "inventory_restocking.md",
    },
    {
        "id": "slow_moving_products",
        "title": "滞销商品处理策略",
        "topic": "slow_moving",
        "content": "滞销商品适合优化标题、主图和促销。",
        "sourcePath": "slow_moving_products.md",
    },
    {
        "id": "fulfillment_risk",
        "title": "履约风险处理策略",
        "topic": "pending_orders",
        "content": "待发货订单需要当天优先处理。",
        "sourcePath": "fulfillment_risk.md",
    },
    {
        "id": "revenue_concentration",
        "title": "收入集中度风险策略",
        "topic": "revenue_concentration",
        "content": "收入集中时需要保护核心商品并寻找第二增长点。",
        "sourcePath": "revenue_concentration.md",
    },
    {
        "id": "promotion_playbook",
        "title": "促销与组合销售策略",
        "topic": "promotion",
        "content": "热销商品可以搭配相关商品做组合销售。",
        "sourcePath": "promotion_playbook.md",
    },
]


def test_infer_query_tags_from_risky_metrics():
    metrics = {
        "pendingOrders": 2,
        "lowStockProducts": [{"productName": "Hot Keyboard"}],
        "slowMovingProducts": [{"productName": "Slow Mouse"}],
        "topProducts": [{"productName": "Hot Keyboard"}],
        "revenueConcentration": 0.75,
    }

    tags = infer_query_tags(metrics)

    assert tags == [
        "pending_orders",
        "low_stock",
        "slow_moving",
        "revenue_concentration",
        "promotion",
    ]


def test_infer_query_tags_ignores_malformed_metrics_without_crashing():
    metrics = {
        "pendingOrders": "N/A",
        "lowStockProducts": "not-a-list",
        "slowMovingProducts": {"bad": "shape"},
        "topProducts": "yes",
        "revenueConcentration": "bad",
    }

    assert infer_query_tags(metrics) == []


def test_infer_query_tags_accepts_numeric_strings():
    metrics = {
        "pendingOrders": "3.0",
        "lowStockProducts": [],
        "slowMovingProducts": [],
        "topProducts": [],
        "revenueConcentration": "0.75",
    }

    assert infer_query_tags(metrics) == ["pending_orders", "revenue_concentration"]


def test_retrieve_seller_insight_knowledge_prioritizes_matching_topics():
    metrics = {
        "pendingOrders": 1,
        "lowStockProducts": [{"productName": "Hot Keyboard"}],
        "slowMovingProducts": [],
        "topProducts": [{"productName": "Hot Keyboard"}],
        "revenueConcentration": 0.2,
    }

    snippets = retrieve_seller_insight_knowledge(metrics, documents=DOCUMENTS, max_snippets=3)

    assert [snippet["id"] for snippet in snippets] == [
        "fulfillment_risk",
        "inventory_restocking",
        "promotion_playbook",
    ]
    assert snippets[0]["score"] > 0
    assert "content" in snippets[0]


def test_retrieve_seller_insight_knowledge_uses_deterministic_tie_order():
    docs = [
        {"id": "z_doc", "title": "A", "topic": "general", "content": "待发货", "sourcePath": "z.md"},
        {"id": "a_doc", "title": "B", "topic": "general", "content": "待发货", "sourcePath": "a.md"},
    ]
    metrics = {
        "pendingOrders": 1,
        "lowStockProducts": [],
        "slowMovingProducts": [],
        "topProducts": [],
        "revenueConcentration": 0,
    }

    snippets = retrieve_seller_insight_knowledge(metrics, documents=docs, max_snippets=2)

    assert [snippet["id"] for snippet in snippets] == ["a_doc", "z_doc"]


def test_retrieve_seller_insight_knowledge_returns_empty_without_signals():
    metrics = {
        "pendingOrders": 0,
        "lowStockProducts": [],
        "slowMovingProducts": [],
        "topProducts": [],
        "revenueConcentration": 0,
    }

    snippets = retrieve_seller_insight_knowledge(metrics, documents=DOCUMENTS)

    assert snippets == []
