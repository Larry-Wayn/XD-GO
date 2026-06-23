# Seller Insight RAG Copilot Design

## 1. 背景

XD-GO 当前已经在卖家销售数据页中加入了 Sales Insight Copilot。后端会聚合卖家的订单、销售额、履约状态、热销商品、低库存商品、滞销商品和收入集中度，再调用 DeepSeek/OpenRouter 生成中文运营简报与行动卡片；如果没有模型密钥、模型超时或返回异常，则回退到 deterministic fallback。

下一步加入 RAG 的目标不是做一个独立聊天机器人，而是让现有 Sales Insight Copilot 在生成经营建议时参考一组电商运营知识文档。这样可以模拟 FDE 在客户现场把客户的运营 SOP、平台规则、知识库模板和实时业务数据连接起来，交付一个业务流程内可用的 AI 工具。

## 2. 目标

第一版 RAG 目标：

- 在现有 `GET /api/sell_order/insights?days=30` 接口中加入知识检索上下文。
- 使用本地 Markdown 知识库增强卖家运营洞察，不新增数据库表。
- 根据当前 seller metrics 自动选择相关知识片段，例如库存补货、滞销商品、待发货订单、收入集中度和促销策略。
- 让模型输出的 briefing 和 action cards 同时基于经营数据和检索知识。
- 在响应 `meta` 中暴露 RAG 状态和引用来源，便于前端展示与面试讲解。
- 保持现有 fallback 能力：知识库缺失、检索失败、模型失败时，原接口仍返回稳定 schema。

## 3. 非目标

第一版明确不做：

- 不做通用多轮聊天。
- 不做买家端 AI assistant。
- 不做用户上传文档。
- 不做后台知识库管理页面。
- 不引入向量数据库或外部 embedding 服务。
- 不做长期 conversation memory。
- 不改数据库 schema。
- 不把真实 API key 写入代码、README、示例文档或提交历史。

这些能力可以作为后续演进方向，但第一版会优先保证小范围、高可信、能演示 FDE 价值。

## 4. 推荐方案

采用轻量本地 RAG：

```text
seller metrics
  -> query tags
  -> local Markdown knowledge retrieval
  -> DeepSeek prompt with metrics + retrieved knowledge
  -> schema validation
  -> frontend insight panel with RAG source badge
```

这个方案适合当前项目，因为：

- 当前 AI 入口已经稳定，RAG 可以接在 `seller_insight_ai.py` 的 prompt 生成之前。
- 当前指标结构清晰，能自动映射到知识主题，不需要用户输入 query。
- 本地 Markdown 知识库便于面试展示，也符合 FDE 的“客户知识沉淀”叙事。
- 不引入向量库可以降低部署复杂度，避免把作品重点从业务交付转移到基础设施。

## 5. 知识库边界

新增目录：

```text
backend/knowledge/seller_ops/
```

第一版包含 5 份 Markdown 文档：

```text
inventory_restocking.md
slow_moving_products.md
fulfillment_risk.md
revenue_concentration.md
promotion_playbook.md
```

每份文档使用统一结构：

```text
# 文档标题

## 适用场景
## 判断信号
## 建议动作
## 注意事项
```

文档内容只写通用电商运营知识，不包含真实商户隐私、真实 API key 或不可公开数据。

## 6. 后端组件设计

新增 `backend/services/seller_insight_knowledge.py`：

- 读取本地 Markdown 知识库。
- 将每份文档解析为结构化 document：
  - `id`
  - `title`
  - `topic`
  - `content`
  - `sourcePath`
- 对文件不存在、目录为空、读取失败做容错，返回空知识列表。

新增 `backend/services/seller_insight_retriever.py`：

- 输入 seller metrics。
- 根据业务信号生成 query tags：
  - `pending_orders`：`pendingOrders > 0`
  - `low_stock`：`lowStockProducts` 非空
  - `slow_moving`：`slowMovingProducts` 非空
  - `revenue_concentration`：`revenueConcentration >= 0.7`
  - `promotion`：有热销商品或滞销商品
- 使用规则匹配和关键词得分检索相关知识文档。
- 返回最多 3 个 knowledge snippets，避免 prompt 过长。

改造 `backend/services/seller_insight_ai.py`：

- 在 `_user_prompt(metrics)` 中加入 `retrievedKnowledge`。
- 更新 system prompt，要求模型同时遵守：
  - 不编造指标。
  - 不编造知识库没有的政策或规则。
  - 每张行动卡优先结合数字证据和知识依据。
  - 仍只输出 JSON，不输出 Markdown。
- 如果模型输出非法 JSON，继续走现有 fallback。

改造 `backend/services/seller_insight_schema.py`：

- 保持 `briefing/cards/metrics/meta` 主结构不变。
- 在 `meta` 中增加：
  - `ragEnabled`
  - `knowledgeSourceCount`
  - `knowledgeSources`

`knowledgeSources` 示例：

```json
[
  {
    "id": "inventory_restocking",
    "title": "库存补货策略",
    "topic": "low_stock"
  }
]
```

## 7. API 响应设计

接口不新增路径，仍复用：

```text
GET /api/sell_order/insights?days=30
```

响应保持当前 `code/message/data` 风格。`data` 示例：

```json
{
  "briefing": "近 30 天店铺存在低库存和待发货风险，建议优先处理履约与补货。",
  "cards": [
    {
      "title": "优先补货低库存商品",
      "priority": "high",
      "recommendation": "对库存低于安全线的商品进行补货。",
      "reason": "低库存会影响热销商品持续转化。",
      "evidence": ["低库存商品 2 个", "近 30 天销售额 1280.00"],
      "metric": "low_stock"
    }
  ],
  "metrics": {},
  "meta": {
    "source": "deepseek",
    "generatedAt": "2026-06-23T10:00:00Z",
    "windowDays": 30,
    "ragEnabled": true,
    "knowledgeSourceCount": 2,
    "knowledgeSources": [
      {
        "id": "inventory_restocking",
        "title": "库存补货策略",
        "topic": "low_stock"
      }
    ]
  }
}
```

当知识库不可用时：

```json
{
  "meta": {
    "ragEnabled": false,
    "knowledgeSourceCount": 0,
    "knowledgeSources": []
  }
}
```

## 8. 前端设计

改造 `frontend/src/views/seller/salesData.vue` 的现有 AI 运营洞察面板：

- 保留原有 briefing 和 action cards。
- 在 header badge 附近增加轻量标识：
  - `知识增强`
  - 或 `无知识库`
- 在 briefing 下方或卡片区域顶部展示知识来源，例如：
  - `参考知识：库存补货策略、滞销商品处理策略`
- 不重做页面结构，不影响今日销售、历史趋势、热销商品区域。

第一版不在每张 card 下展开全文引用，只展示来源标题，保证页面干净。

## 9. 错误处理

RAG 的错误处理遵循“不影响原有销售洞察”的原则：

- 知识库目录不存在：返回空知识来源，模型仍可只基于 metrics 生成。
- Markdown 文件读取失败：跳过失败文件，继续处理其他文件。
- 检索没有命中：`ragEnabled=false`，不阻断模型调用。
- 模型调用失败：返回 fallback payload。
- 模型返回非法 JSON：返回 fallback payload。
- fallback payload 也要包含 `ragEnabled` 和空 `knowledgeSources`，确保前端不需要特殊判断。

## 10. 测试计划

后端测试：

- seller metrics 存在低库存商品时，retriever 命中 `inventory_restocking`。
- seller metrics 存在滞销商品时，retriever 命中 `slow_moving_products`。
- seller metrics 存在 pending orders 时，retriever 命中 `fulfillment_risk`。
- 高收入集中度时，retriever 命中 `revenue_concentration`。
- 知识库目录为空或不存在时，接口仍返回 `code: 200`。
- 无 API key 时，响应 `meta.source == "fallback"`，且包含 RAG meta 字段。
- mock DeepSeek 返回合法 JSON 时，响应 `meta.source == "deepseek"` 且包含 knowledge sources。
- mock DeepSeek 抛异常、超时、非法 JSON 时，schema 稳定并回退 fallback。

前端验证：

- `npm run build` 通过。
- 销售数据页能显示 `知识增强` badge。
- 有知识来源时展示来源标题。
- 无知识来源或 fallback 时页面不报错。
- 切换 7 / 30 / 90 天后，销售图表和 RAG 洞察同步刷新。

## 11. 面试叙事

这个 RAG 改造体现的 FDE 能力：

- 需求转译：把“希望 AI 帮卖家经营”拆解为数据指标、知识库、模型生成和前端交互。
- 业务知识沉淀：将运营 SOP 转成可检索 Markdown 知识库。
- AI 工程落地：把 RAG 嵌入现有业务接口，而不是做孤立 demo。
- 可靠性设计：模型失败、知识库缺失、网络异常时都能 fallback。
- 客户成功视角：输出的是卖家可执行行动卡，而不是泛泛聊天回答。
- 可复制交付：知识库文档和检索规则可迁移到其他电商客户场景。

## 12. 实施顺序

推荐按以下顺序实现：

1. 新增本地 Markdown 知识库。
2. 实现知识库读取服务。
3. 实现基于 metrics 的轻量 retriever。
4. 扩展 insight schema 的 RAG meta。
5. 改造 DeepSeek prompt 输入。
6. 更新 fallback payload。
7. 更新前端 badge 和知识来源展示。
8. 增加后端单元测试和前端 build 验证。
9. 更新 FDE 项目说明文档。

## 13. 验收标准

第一版完成后应满足：

- 卖家访问 `/api/sell_order/insights?days=30` 能看到稳定响应。
- 响应中包含 `meta.ragEnabled`、`meta.knowledgeSourceCount`、`meta.knowledgeSources`。
- 当前销售数据触发低库存、滞销、履约或集中度风险时，能检索到对应运营知识。
- 前端 AI 面板能展示知识增强状态和来源标题。
- 没有真实 API key 被提交。
- 后端测试通过。
- 前端 build 通过。
