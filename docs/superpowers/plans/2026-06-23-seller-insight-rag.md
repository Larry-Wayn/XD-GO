# Seller Insight RAG Copilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add lightweight RAG to the existing seller Sales Insight Copilot so AI recommendations combine live seller metrics with local e-commerce operations knowledge.

**Architecture:** Keep the existing `/api/sell_order/insights` API and Vue sales page. Add a local Markdown knowledge base, a focused loader, a metrics-driven retriever, RAG metadata in the insight schema, and pass retrieved snippets into the DeepSeek prompt. Avoid database schema changes, external vector databases, document upload, or a new chat UI.

**Tech Stack:** Flask, SQLAlchemy, pytest, Vue 3, Element Plus, Vite, Markdown files, OpenAI-compatible DeepSeek chat completions.

---

## File Structure

- Create `backend/knowledge/seller_ops/inventory_restocking.md`: seller inventory and replenishment playbook.
- Create `backend/knowledge/seller_ops/slow_moving_products.md`: stagnant inventory handling playbook.
- Create `backend/knowledge/seller_ops/fulfillment_risk.md`: pending order and fulfillment risk playbook.
- Create `backend/knowledge/seller_ops/revenue_concentration.md`: revenue concentration risk playbook.
- Create `backend/knowledge/seller_ops/promotion_playbook.md`: promotion and bundle strategy playbook.
- Create `backend/services/seller_insight_knowledge.py`: read and normalize local Markdown knowledge documents.
- Create `backend/services/seller_insight_retriever.py`: infer business issue tags from metrics and retrieve relevant knowledge snippets.
- Modify `backend/services/seller_insight_schema.py`: add RAG meta normalization while keeping the existing response shape stable.
- Modify `backend/services/seller_insight_fallback.py`: make fallback responses include stable RAG meta fields.
- Modify `backend/services/seller_insight_ai.py`: include retrieved knowledge in model input and update prompt rules.
- Modify `backend/views/seller_insights.py`: retrieve knowledge after metrics aggregation and pass snippets into AI generation.
- Create `backend/tests/test_seller_insight_knowledge.py`: unit tests for document loading.
- Create `backend/tests/test_seller_insight_retriever.py`: unit tests for metrics-to-knowledge retrieval.
- Modify `backend/tests/test_seller_insights.py`: integration tests for endpoint RAG metadata and fallback shape.
- Modify `backend/tests/test_seller_insights_deepseek.py`: DeepSeek prompt tests and compatibility cleanup.
- Modify `frontend/src/views/seller/salesData.vue`: show RAG badge and knowledge source titles in the existing AI panel.
- Modify `FDE_PROJECT_GUIDE.md`: document the new RAG capability and interview talking points.

---

### Task 1: Add Seller Operations Knowledge Base

**Files:**
- Create: `backend/knowledge/seller_ops/inventory_restocking.md`
- Create: `backend/knowledge/seller_ops/slow_moving_products.md`
- Create: `backend/knowledge/seller_ops/fulfillment_risk.md`
- Create: `backend/knowledge/seller_ops/revenue_concentration.md`
- Create: `backend/knowledge/seller_ops/promotion_playbook.md`

- [ ] **Step 1: Create local Markdown knowledge documents**

Add `backend/knowledge/seller_ops/inventory_restocking.md`:

```markdown
# 库存补货策略

## 适用场景
当热销商品库存低于安全库存线，或近期销量接近当前库存时，卖家应优先处理补货与库存准确性。

## 判断信号
- 商品当前库存小于等于 5。
- 商品近 7 / 30 / 90 天有销量，但可售库存已经接近售出数量。
- 热销商品出现在低库存列表中。

## 建议动作
- 优先确认实物库存和系统库存是否一致。
- 对仍有稳定销量的商品设置补货优先级。
- 如果短期无法补货，降低推广曝光或临时下架，避免超卖。
- 对高销量低库存商品设置安全库存提醒。

## 注意事项
低库存建议必须结合近期销量判断。没有销量的低库存商品不应直接判定为高优先级补货。
```

Add `backend/knowledge/seller_ops/slow_moving_products.md`:

```markdown
# 滞销商品处理策略

## 适用场景
当商品库存较高但当前分析窗口内销量为 0，卖家需要判断是曝光不足、价格不合适，还是商品信息不清晰。

## 判断信号
- 商品库存大于等于 20。
- 商品近 7 / 30 / 90 天销量为 0。
- 店铺有整体订单，但部分商品长期没有转化。

## 建议动作
- 优先优化标题、主图和商品描述，突出核心卖点。
- 对滞销商品设置限时折扣、满减或组合销售。
- 将滞销商品与热销商品做搭配推荐。
- 对长期无转化商品降低采购或补货优先级。

## 注意事项
滞销处理应先做小范围价格和页面优化测试，避免直接大幅降价损害利润。
```

Add `backend/knowledge/seller_ops/fulfillment_risk.md`:

```markdown
# 履约风险处理策略

## 适用场景
当店铺存在待发货订单时，卖家需要优先处理履约，以降低买家体验风险和售后压力。

## 判断信号
- pending 状态订单数量大于 0。
- pending 订单占总订单比例较高。
- 热销商品相关订单处于待发货状态。

## 建议动作
- 当天优先处理 pending 订单并更新物流状态。
- 将待发货订单按下单时间排序，先处理等待时间更长的订单。
- 如果缺货导致无法发货，及时联系买家并同步预计处理时间。
- 对待发货占比较高的商品检查库存准确性和拣货流程。

## 注意事项
履约建议要优先于促销建议。未解决待发货风险前，不应继续放大相关商品曝光。
```

Add `backend/knowledge/seller_ops/revenue_concentration.md`:

```markdown
# 收入集中度风险策略

## 适用场景
当店铺大部分收入来自少数商品时，卖家需要保护核心商品，同时寻找第二增长点。

## 判断信号
- Top 3 商品收入占比大于等于 70%。
- 第一热销商品贡献了明显高于其他商品的收入。
- 核心商品同时存在低库存或履约风险。

## 建议动作
- 优先保障核心商品库存、价格稳定和履约质量。
- 为核心商品准备替代款、配件或组合销售商品。
- 分析第二梯队商品，选择有潜力商品进行页面优化和促销测试。
- 避免所有推广预算只集中在单一商品上。

## 注意事项
收入集中不是负面信号，但当核心商品缺货、差评或履约异常时，会放大经营风险。
```

Add `backend/knowledge/seller_ops/promotion_playbook.md`:

```markdown
# 促销与组合销售策略

## 适用场景
当店铺存在热销商品或滞销商品时，可以通过促销、组合销售和页面优化提升转化效率。

## 判断信号
- 店铺存在明确热销商品。
- 店铺存在库存高但销量低的商品。
- 买家可能同时购买互补商品。

## 建议动作
- 将热销商品作为流量入口，搭配相关商品做组合销售。
- 对滞销商品做小额折扣、限时活动或赠品测试。
- 在商品详情页突出适用场景、规格和售后承诺。
- 优先测试低风险促销，观察订单量和库存变化。

## 注意事项
促销建议必须结合库存和履约能力。库存不足或待发货压力较高时，不应继续扩大促销。
```

- [ ] **Step 2: Verify no secrets exist in knowledge documents**

Run:

```bash
rg -n "sk-|API_KEY|DEEPSEEK_API_KEY|OPENAI_API_KEY" backend/knowledge/seller_ops
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add backend/knowledge/seller_ops
git commit -m "docs: add seller operations knowledge base"
```

---

### Task 2: Implement Knowledge Loader With Tests

**Files:**
- Create: `backend/tests/test_seller_insight_knowledge.py`
- Create: `backend/services/seller_insight_knowledge.py`

- [ ] **Step 1: Write failing tests for knowledge loading**

Create `backend/tests/test_seller_insight_knowledge.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=.. pytest tests/test_seller_insight_knowledge.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `backend.services.seller_insight_knowledge`.

- [ ] **Step 3: Implement the knowledge loader**

Create `backend/services/seller_insight_knowledge.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=.. pytest tests/test_seller_insight_knowledge.py -v
```

Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/services/seller_insight_knowledge.py backend/tests/test_seller_insight_knowledge.py
git commit -m "feat: load seller insight knowledge"
```

---

### Task 3: Implement Metrics-Driven Retriever With Tests

**Files:**
- Create: `backend/tests/test_seller_insight_retriever.py`
- Create: `backend/services/seller_insight_retriever.py`

- [ ] **Step 1: Write failing tests for tag inference and retrieval**

Create `backend/tests/test_seller_insight_retriever.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=.. pytest tests/test_seller_insight_retriever.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `backend.services.seller_insight_retriever`.

- [ ] **Step 3: Implement the retriever**

Create `backend/services/seller_insight_retriever.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=.. pytest tests/test_seller_insight_retriever.py -v
```

Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/services/seller_insight_retriever.py backend/tests/test_seller_insight_retriever.py
git commit -m "feat: retrieve seller insight knowledge"
```

---

### Task 4: Extend Insight Schema and Fallback RAG Metadata

**Files:**
- Modify: `backend/services/seller_insight_schema.py`
- Modify: `backend/services/seller_insight_fallback.py`
- Modify: `backend/tests/test_seller_insights.py`

- [ ] **Step 1: Add failing tests for RAG meta in fallback payloads**

Modify `backend/tests/test_seller_insights.py`.

Update `test_empty_store_fallback_returns_safe_payload` assertions:

```python
    assert payload['meta']['source'] == 'fallback'
    assert payload['meta']['ragEnabled'] is False
    assert payload['meta']['knowledgeSourceCount'] == 0
    assert payload['meta']['knowledgeSources'] == []
    assert payload['metrics']['orderCount'] == 0
```

Update `test_seller_insights_endpoint_returns_fallback_payload` assertions:

```python
    assert body['data']['meta']['source'] == 'fallback'
    assert body['data']['meta']['windowDays'] == 30
    assert body['data']['meta']['ragEnabled'] is False
    assert body['data']['meta']['knowledgeSourceCount'] == 0
    assert body['data']['meta']['knowledgeSources'] == []
    assert body['data']['briefing']
    assert body['data']['cards']
```

Add a new unit test:

```python
def test_build_fallback_ignores_knowledge_sources_for_stable_degraded_mode(app):
    with app.app_context():
        _seed_store()
        metrics = get_seller_insight_metrics('seller_1', days=30)
        payload = build_fallback_insight(metrics, knowledge_sources=[{
            "id": "inventory_restocking",
            "title": "库存补货策略",
            "topic": "low_stock",
            "content": "补货内容",
            "score": 100,
        }])

    assert payload['meta']['source'] == 'fallback'
    assert payload['meta']['ragEnabled'] is False
    assert payload['meta']['knowledgeSourceCount'] == 0
    assert payload['meta']['knowledgeSources'] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=.. pytest tests/test_seller_insights.py::test_empty_store_fallback_returns_safe_payload tests/test_seller_insights.py::test_seller_insights_endpoint_returns_fallback_payload tests/test_seller_insights.py::test_build_fallback_ignores_knowledge_sources_for_stable_degraded_mode -v
```

Expected: FAIL because `ragEnabled`, `knowledgeSourceCount`, and `knowledgeSources` are missing, and `build_fallback_insight` does not accept `knowledge_sources`.

- [ ] **Step 3: Extend schema helpers**

Modify `backend/services/seller_insight_schema.py`.

Add these helpers above `build_insight_payload`:

```python
def normalize_knowledge_sources(knowledge_sources):
    if not isinstance(knowledge_sources, list):
        return []

    normalized = []
    seen = set()
    for source in knowledge_sources:
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("id") or "").strip()
        if not source_id or source_id in seen:
            continue
        seen.add(source_id)
        normalized.append({
            "id": source_id,
            "title": str(source.get("title") or "运营知识"),
            "topic": str(source.get("topic") or "general"),
        })
    return normalized[:5]
```

Replace `build_insight_payload` with:

```python
def build_insight_payload(briefing, cards, metrics, source, knowledge_sources=None, rag_enabled=None):
    normalized_cards = normalize_cards(cards)
    if not normalized_cards:
        normalized_cards = [normalize_card({})]
    window_days = int(metrics.get("windowDays", 30) or 30)
    normalized_sources = normalize_knowledge_sources(knowledge_sources)
    enabled = bool(normalized_sources) if rag_enabled is None else bool(rag_enabled)
    if not enabled:
        normalized_sources = []
    return {
        "briefing": str(briefing or "暂无足够数据生成运营简报。"),
        "cards": normalized_cards,
        "metrics": metrics,
        "meta": {
            "source": source,
            "generatedAt": utc_now_iso(),
            "windowDays": window_days,
            "ragEnabled": enabled,
            "knowledgeSourceCount": len(normalized_sources),
            "knowledgeSources": normalized_sources,
        }
    }
```

- [ ] **Step 4: Update fallback signature**

Modify `backend/services/seller_insight_fallback.py`.

Change the function signature:

```python
def build_fallback_insight(metrics, knowledge_sources=None):
```

Leave all fallback calls to `build_insight_payload` using source `"fallback"` without passing `knowledge_sources`. This intentionally keeps fallback in degraded mode with `ragEnabled=false`, even when retrieval was available.

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=.. pytest tests/test_seller_insights.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/services/seller_insight_schema.py backend/services/seller_insight_fallback.py backend/tests/test_seller_insights.py
git commit -m "feat: add rag metadata to seller insights"
```

---

### Task 5: Add RAG Context to DeepSeek Generation

**Files:**
- Modify: `backend/services/seller_insight_ai.py`
- Modify: `backend/tests/test_seller_insights_deepseek.py`

- [ ] **Step 1: Add failing DeepSeek tests for retrieved knowledge in prompt**

Modify `backend/tests/test_seller_insights_deepseek.py`.

Update `test_deepseek_success_uses_chat_completions` call:

```python
    knowledge_snippets = [{
        "id": "inventory_restocking",
        "title": "库存补货策略",
        "topic": "low_stock",
        "content": "低库存商品需要确认库存和补货。",
        "score": 100,
    }]

    payload = generate_seller_insight(
        _metrics(app),
        client=client,
        knowledge_snippets=knowledge_snippets,
    )
```

Update assertions:

```python
    assert payload['meta']['source'] == 'deepseek'
    assert payload['meta']['ragEnabled'] is True
    assert payload['meta']['knowledgeSourceCount'] == 1
    assert payload['meta']['knowledgeSources'][0]['title'] == '库存补货策略'
    assert payload['briefing'] == 'DeepSeek generated briefing'
    assert client.chat.completions.kwargs['model'] == 'deepseek-v4-flash'
    assert 'response_format' not in client.chat.completions.kwargs

    user_message = client.chat.completions.kwargs['messages'][1]
    prompt_payload = json.loads(user_message['content'])
    assert prompt_payload['retrievedKnowledge'][0]['title'] == '库存补货策略'
    assert prompt_payload['retrievedKnowledge'][0]['content'] == '低库存商品需要确认库存和补货。'
```

Add `import json` at the top of the test file.

Add this fallback test:

```python
def test_deepseek_exception_returns_fallback_without_rag_enabled(app, monkeypatch):
    class BrokenCompletions:
        def create(self, **kwargs):
            raise RuntimeError('network down')

    class BrokenChat:
        completions = BrokenCompletions()

    class BrokenClient:
        chat = BrokenChat()

    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-key')

    payload = generate_seller_insight(
        _metrics(app),
        client=BrokenClient(),
        knowledge_snippets=[{
            "id": "inventory_restocking",
            "title": "库存补货策略",
            "topic": "low_stock",
            "content": "低库存商品需要确认库存和补货。",
        }],
    )

    assert payload['meta']['source'] == 'fallback'
    assert payload['meta']['ragEnabled'] is False
    assert payload['meta']['knowledgeSources'] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=.. pytest tests/test_seller_insights_deepseek.py -v
```

Expected: FAIL because `generate_seller_insight` does not accept `knowledge_snippets` and prompt lacks `retrievedKnowledge`.

- [ ] **Step 3: Update AI prompt and function signatures**

Modify `backend/services/seller_insight_ai.py`.

Replace `SYSTEM_PROMPT` with:

```python
SYSTEM_PROMPT = """
你是一名电商卖家运营分析师。你会基于结构化店铺指标和检索到的运营知识，输出简洁、可执行、面向卖家的中文运营洞察。
规则：
1. 不要编造指标、商品、订单状态、平台政策或知识库没有提供的规则。
2. 每张行动卡必须引用输入中已有的数字证据。
3. 如果 retrievedKnowledge 非空，优先结合相关知识给出建议，但不要逐字照抄知识库。
4. 优先给出具体动作，例如补货、处理待发货订单、优化滞销品，而不是泛泛建议。
5. 只输出 JSON 对象，不要输出 Markdown 或解释文字。
6. JSON 对象必须只包含 briefing 和 cards 字段，并符合请求中的 schema。
""".strip()
```

Replace `_user_prompt` with:

```python
def _user_prompt(metrics, knowledge_snippets=None):
    return json.dumps({
        "metrics": metrics,
        "retrievedKnowledge": knowledge_snippets or [],
        "requiredOutputSchema": SELLER_INSIGHT_JSON_SCHEMA,
    }, ensure_ascii=False)
```

Replace `generate_seller_insight` with:

```python
def generate_seller_insight(metrics, client=None, knowledge_snippets=None):
    fallback_payload = build_fallback_insight(metrics, knowledge_sources=knowledge_snippets)
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
                {"role": "user", "content": _user_prompt(metrics, knowledge_snippets)}
            ],
            temperature=0.2,
        )
        briefing, cards = _parse_model_payload(_extract_output_text(response))
        return build_insight_payload(
            briefing,
            cards,
            metrics,
            PROVIDER_SOURCE,
            knowledge_sources=knowledge_snippets,
            rag_enabled=bool(knowledge_snippets),
        )
    except Exception:
        return fallback_payload
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=.. pytest tests/test_seller_insights_deepseek.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/seller_insight_ai.py backend/tests/test_seller_insights_deepseek.py
git commit -m "feat: add rag context to seller insight ai"
```

---

### Task 6: Wire Retriever Into Insights Endpoint

**Files:**
- Modify: `backend/views/seller_insights.py`
- Modify: `backend/tests/test_seller_insights.py`

- [ ] **Step 1: Add failing endpoint integration test**

Add to `backend/tests/test_seller_insights.py`:

```python
def test_seller_insights_endpoint_passes_knowledge_to_ai(app, client, monkeypatch):
    captured = {}

    def fake_generate_seller_insight(metrics, knowledge_snippets=None):
        captured["metrics"] = metrics
        captured["knowledge_snippets"] = knowledge_snippets
        from backend.services.seller_insight_schema import build_insight_payload
        return build_insight_payload(
            "知识增强简报",
            [{
                "title": "补货建议",
                "priority": "high",
                "recommendation": "优先补货热销低库存商品。",
                "reason": "低库存商品需要确认库存和补货。",
                "evidence": ["低库存商品 1 个"],
                "metric": "low_stock",
            }],
            metrics,
            "deepseek",
            knowledge_sources=knowledge_snippets,
            rag_enabled=True,
        )

    monkeypatch.setattr(
        "backend.views.seller_insights.generate_seller_insight",
        fake_generate_seller_insight,
    )

    with app.app_context():
        _seed_store()

    response = client.get(
        '/api/sell_order/insights?days=30',
        headers={'Authorization': f'Bearer {_token("seller_1")}'},
    )

    body = response.get_json()
    assert response.status_code == 200
    assert body['data']['meta']['ragEnabled'] is True
    assert body['data']['meta']['knowledgeSourceCount'] >= 1
    assert captured["knowledge_snippets"]
    assert any(
        snippet["id"] == "inventory_restocking"
        for snippet in captured["knowledge_snippets"]
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=.. pytest tests/test_seller_insights.py::test_seller_insights_endpoint_passes_knowledge_to_ai -v
```

Expected: FAIL because endpoint does not retrieve or pass `knowledge_snippets`.

- [ ] **Step 3: Wire retriever into route**

Modify `backend/views/seller_insights.py`.

Add import:

```python
from backend.services.seller_insight_retriever import retrieve_seller_insight_knowledge
```

Replace endpoint body:

```python
        days = parse_insight_days(request.args.get('days', 30))
        metrics = get_seller_insight_metrics(current_user.userid, days=days)
        knowledge_snippets = retrieve_seller_insight_knowledge(metrics)
        insight = generate_seller_insight(metrics, knowledge_snippets=knowledge_snippets)
```

- [ ] **Step 4: Run backend seller insight tests**

Run:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=.. pytest tests/test_seller_insights.py tests/test_seller_insights_deepseek.py tests/test_seller_insight_knowledge.py tests/test_seller_insight_retriever.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/views/seller_insights.py backend/tests/test_seller_insights.py
git commit -m "feat: wire rag retrieval into seller insights"
```

---

### Task 7: Add RAG UI Badge and Knowledge Sources

**Files:**
- Modify: `frontend/src/views/seller/salesData.vue`

- [ ] **Step 1: Update reactive meta state**

In `frontend/src/views/seller/salesData.vue`, extend `insightMeta`:

```js
    const insightMeta = reactive({
      source: '',
      generatedAt: '',
      windowDays: 30,
      ragEnabled: false,
      knowledgeSourceCount: 0,
      knowledgeSources: []
    })
```

Update `resetInsightState`:

```js
      Object.assign(insightMeta, {
        source: '',
        generatedAt: '',
        windowDays: Number(timeRange.value),
        ragEnabled: false,
        knowledgeSourceCount: 0,
        knowledgeSources: []
      })
```

- [ ] **Step 2: Add computed labels**

Add after `sourceTagType`:

```js
    const ragLabel = computed(() => insightMeta.ragEnabled ? '知识增强' : '无知识库')
    const ragTagType = computed(() => insightMeta.ragEnabled ? 'success' : 'info')
    const knowledgeSourceTitles = computed(() => {
      const sources = Array.isArray(insightMeta.knowledgeSources)
        ? insightMeta.knowledgeSources
        : []
      return sources.map(source => source.title).filter(Boolean)
    })
```

Return them from `setup()`:

```js
      ragLabel,
      ragTagType,
      knowledgeSourceTitles,
```

- [ ] **Step 3: Update template badge and source display**

In the header, after the source tag:

```vue
            <el-tag :type="ragTagType" size="small">
              {{ ragLabel }}
            </el-tag>
```

After the briefing box:

```vue
        <div v-if="knowledgeSourceTitles.length" class="knowledge-source-box">
          <span class="knowledge-source-label">参考知识：</span>
          <el-tag
            v-for="title in knowledgeSourceTitles"
            :key="title"
            size="small"
            effect="plain"
          >
            {{ title }}
          </el-tag>
        </div>
```

- [ ] **Step 4: Add scoped styles**

Add near `.briefing-box`:

```css
.knowledge-source-box {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 13px;
}

.knowledge-source-label {
  font-weight: 600;
}
```

- [ ] **Step 5: Run frontend build**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS and Vite reports a successful production build.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/seller/salesData.vue
git commit -m "feat: show rag sources in seller insight panel"
```

---

### Task 8: Update FDE Project Guide

**Files:**
- Modify: `FDE_PROJECT_GUIDE.md`

- [ ] **Step 1: Add RAG capability description**

In `FDE_PROJECT_GUIDE.md`, add this section after the Sales Insight Copilot feature list:

```markdown
### 4.4 RAG 知识库增强

当前版本进一步加入轻量 RAG 能力，将卖家实时经营指标与本地电商运营知识库结合：

- 后端新增 `backend/knowledge/seller_ops/` 运营知识库
- 覆盖库存补货、滞销处理、履约风险、收入集中度和促销组合策略
- 后端根据销售指标自动检索相关知识片段
- DeepSeek 生成运营洞察时同时参考结构化销售数据和检索知识
- 前端 AI 面板展示“知识增强”状态与参考知识来源
- 模型不可用或知识库不可用时仍保持 fallback，保证演示稳定性

这一改造体现了 FDE 在客户现场常见的交付方式：将客户业务 SOP 和平台经验沉淀为知识库，再接入真实业务数据与大模型，形成可复用的 AI 工作流。
```

- [ ] **Step 2: Add interview talking point**

In the FDE key-points section, add:

```markdown
- **RAG 场景落地**：不是单独做聊天机器人，而是在卖家经营分析流程中检索运营 SOP，并生成带业务依据的行动建议。
```

- [ ] **Step 3: Verify no real key appears in docs**

Run:

```bash
rg -n "<real-secret-pattern>" FDE_PROJECT_GUIDE.md docs backend/knowledge
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add FDE_PROJECT_GUIDE.md
git commit -m "docs: document seller insight rag workflow"
```

---

### Task 9: Final Verification

**Files:**
- No direct edits.

- [ ] **Step 1: Run focused backend tests**

Run:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=.. pytest tests/test_seller_insights.py tests/test_seller_insights_deepseek.py tests/test_seller_insight_knowledge.py tests/test_seller_insight_retriever.py -v
```

Expected: PASS.

- [ ] **Step 2: Run frontend build**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 3: Inspect final diff**

Run:

```bash
git status --short
git diff --stat HEAD
```

Expected: only expected uncommitted files remain. `backend/services/__pycache__/` should not be staged or committed.

- [ ] **Step 4: Optional local smoke test**

Start backend:

```bash
cd backend
source .venv/bin/activate
set -a
source ../.env
set +a
PYTHONPATH=.. flask --app app run --host 0.0.0.0 --port 5001
```

Start frontend:

```bash
cd frontend
npm run dev -- --host 0.0.0.0
```

Open:

```text
http://localhost:5173/
```

Login:

```text
jane_smith / seller123
```

Expected: seller sales page shows AI 运营洞察, source badge, RAG badge, and knowledge source titles when risky metrics match the knowledge base.

Stop services:

```bash
lsof -ti tcp:5001 | xargs kill
lsof -ti tcp:5173 | xargs kill
```

- [ ] **Step 5: Confirm no generated or secret files are staged**

Run:

```bash
git status --short
```

Expected: no staged generated files. Do not commit:

```text
backend/services/__pycache__/
.env
dist/
node_modules/
```

---

## Self-Review Notes

- Spec coverage: this plan covers the local Markdown knowledge base, loader, retriever, AI prompt integration, stable RAG meta, endpoint wiring, frontend display, tests, docs, and verification.
- Scope check: this plan intentionally excludes vector databases, document upload, chat UI, database schema changes, and buyer-side AI.
- Type consistency: the plan consistently uses `knowledge_snippets` for prompt input and `knowledgeSources` / `knowledgeSourceCount` / `ragEnabled` in API meta.
- Reliability: fallback mode remains stable and does not require RAG or model availability.
