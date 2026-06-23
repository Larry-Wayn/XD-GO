from backend.services.seller_insight_knowledge import (
    load_seller_ops_knowledge,
    source_from_document,
)


def test_load_seller_ops_knowledge_from_directory(tmp_path):
    doc = tmp_path / "inventory_restocking.md"
    doc.write_text(
        "# 库存补货策略\n\n## 适用场景\n低库存商品需要补货。\n\n## 建议动作\n确认库存。",
        encoding="utf-8",
    )

    documents = load_seller_ops_knowledge(tmp_path)

    assert len(documents) == 1
    assert documents[0]["id"] == "inventory_restocking"
    assert documents[0]["title"] == "库存补货策略"
    assert documents[0]["topic"] == "low_stock"
    assert "低库存商品需要补货" in documents[0]["content"]
    assert documents[0]["sourcePath"].endswith("inventory_restocking.md")


def test_load_seller_ops_knowledge_missing_directory_returns_empty(tmp_path):
    documents = load_seller_ops_knowledge(tmp_path / "missing")

    assert documents == []


def test_source_from_document_removes_prompt_content():
    document = {
        "id": "inventory_restocking",
        "title": "库存补货策略",
        "topic": "low_stock",
        "content": "long internal content",
        "sourcePath": "/tmp/inventory_restocking.md",
    }

    assert source_from_document(document) == {
        "id": "inventory_restocking",
        "title": "库存补货策略",
        "topic": "low_stock",
    }
