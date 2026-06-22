# FDE Sales Insight Copilot Design

## Goal

Turn XD-GO from a functional online shopping coursework project into a credible FDE interview portfolio piece by adding a seller-facing AI operations feature: a Sales Insight Copilot that analyzes the seller's recent store data and translates it into a concise operations briefing plus prioritized action cards.

The feature should demonstrate the FDE pattern clearly: understand an existing workflow, identify an operational pain point, integrate model capability into production-style backend boundaries, preserve demo reliability, and explain business impact.

## Selected Direction

We considered three AI transformation storylines:

1. Buyer Shopping Copilot
2. Seller Operations Copilot
3. Full AI Transformation Layer

The selected direction is Seller Operations Copilot. Within that direction, the selected anchor workflow is Sales Insight Copilot rather than listing generation or order-response drafting. The selected output style is:

- AI Operations Briefing
- Prioritized Action Cards

The default analysis window is the most recent 30 days.

## Existing Project Context

XD-GO is a Flask + Vue online shopping system with buyer and seller flows.

Relevant backend structure:

- `backend/models.py` defines `User`, `Product`, `Order`, and `OrderItem`.
- `backend/views/seller.py` contains seller-facing APIs.
- `backend/views/product.py` exposes buyer product listing, detail, category, and search APIs.
- `backend/views/buyer_order.py` and `backend/views/buyer_cart.py` manage buyer order and cart flows.

Relevant frontend structure:

- `frontend/src/views/seller/salesData.vue` is the natural integration point for seller insights.
- `frontend/src/api/seller.js` already groups seller API calls.
- `frontend/src/router/modules/seller.js` owns seller routes.
- `frontend/package.json` shows Vue 3, Pinia, Element Plus, ECharts, Axios, and Vite.

## User Experience

The seller opens the existing seller sales data page. Above the existing charts and metrics, the page shows an Insight panel with three states:

1. Loading: the system is computing seller metrics and generating insight text.
2. Insight available: the panel displays an operations briefing and action cards.
3. Empty or fallback: the panel explains that there is not enough data or that local rules generated the insight because the model call was unavailable.

The panel contains:

- A short operations briefing in Chinese, written for a seller/operator.
- 3 to 5 action cards.
- Each action card has a title, priority, recommendation, reason, and supporting evidence.
- A small source badge showing `OpenAI` or `Fallback`.
- The analysis window, generated time, and key metric summary.

Example action card types:

- Prioritize pending shipments when pending order count is high.
- Restock products when available stock is low relative to recent sold quantity.
- Promote slow-moving products when inventory is high but recent sales are weak.
- Protect best sellers when a small number of products contribute most revenue.

## Backend Architecture

Add a backend-first insight service. The frontend should never call OpenAI directly and should never receive the API key.

Proposed backend files:

- `backend/views/seller_insights.py`
  - Flask blueprint route for `GET /seller/insights`.
  - Authenticates the seller using the existing token pattern.
  - Parses `days`, defaulting to 30 and enforcing a bounded range.
  - Returns the insight payload.

- `backend/services/seller_insight_metrics.py`
  - Queries `Order`, `OrderItem`, and `Product` for the current seller.
  - Builds deterministic metrics for the selected window.
  - Keeps SQLAlchemy/query logic isolated from model prompting.

- `backend/services/seller_insight_ai.py`
  - Builds the OpenAI prompt from structured metrics.
  - Calls the OpenAI Responses API when `OPENAI_API_KEY` is present.
  - Requests structured JSON output for briefing and cards.
  - Validates model output before returning it.

- `backend/services/seller_insight_fallback.py`
  - Generates deterministic local insights from the same metrics.
  - Handles no-key, timeout, invalid JSON, and empty-data cases.

- `backend/services/seller_insight_schema.py`
  - Defines response shape constants or lightweight validation helpers.
  - Keeps API response consistency visible and testable.

The OpenAI client should read configuration from environment variables:

- `OPENAI_API_KEY`: required only for live model generation.
- `OPENAI_MODEL`: optional, defaults to a current compact production model chosen during implementation.
- `OPENAI_TIMEOUT_SECONDS`: optional bounded timeout.

A `.env.example` may document these variables. Real keys must never be committed.

## API Contract

Endpoint:

```http
GET /seller/insights?days=30
Authorization: Bearer <token>
```

Successful response:

```json
{
  "status": 200,
  "message": "获取卖家运营洞察成功",
  "data": {
    "briefing": "近30天店铺收入主要来自...",
    "cards": [
      {
        "title": "优先处理待发货订单",
        "priority": "high",
        "recommendation": "今天优先处理待发货订单，降低履约风险。",
        "reason": "待发货订单数量高于近期平均水平。",
        "evidence": ["待发货订单: 8", "近30天订单: 24"],
        "metric": "pending_orders"
      }
    ],
    "metrics": {
      "windowDays": 30,
      "orderCount": 24,
      "revenue": 2388.5,
      "pendingOrders": 8,
      "topProducts": [
        {
          "productId": "p001",
          "productName": "无线鼠标",
          "quantitySold": 12,
          "revenue": 598.8,
          "stock": 5
        }
      ]
    },
    "meta": {
      "source": "openai",
      "generatedAt": "2026-06-22T10:30:00Z",
      "windowDays": 30
    }
  }
}
```

Fallback response has the same shape with `meta.source` set to `fallback`.

Empty-data response should still return `status: 200` with a helpful briefing and no misleading recommendations.

Authentication or role failures should follow the existing project's API style and return an appropriate error response.

## Metrics Design

The metric service should compute a compact fact pack for the model and fallback generator:

- Window start and end.
- Total order count.
- Total revenue.
- Order counts by status: unpaid, pending, shipped, delivered.
- Top products by revenue and quantity.
- Low-stock products among products owned by the seller.
- Slow-moving products with stock but low or zero recent sold quantity.
- Revenue concentration, such as top 3 product revenue share.

The model prompt should use only this fact pack. It should not receive raw user records, passwords, payment secrets, or unrelated personal data.

## Model Behavior

The OpenAI path should request a strict structured response with:

- `briefing`: one concise Chinese paragraph.
- `cards`: 3 to 5 cards, each with title, priority, recommendation, reason, evidence, and metric.

The prompt should instruct the model to:

- Act as a practical ecommerce operations analyst.
- Avoid fabricating products or metrics not present in the fact pack.
- Cite numeric evidence inside each card.
- Prefer concrete seller actions over generic advice.
- Keep the tone professional and interview-demo friendly.

If the API key is missing, the request times out, the client raises an exception, or validation fails, the service must return fallback output from the deterministic generator.

## Frontend Design

Integrate into `frontend/src/views/seller/salesData.vue`.

Add a new top panel before existing charts:

- Header: `AI 运营洞察`
- Source badge: `OpenAI` or `Fallback`
- Generated time and analysis window.
- Briefing block.
- Action-card grid.
- Empty state when no orders exist in the analysis window.
- Error state only when both metric generation and fallback generation fail.

Add a seller API wrapper in `frontend/src/api/seller.js`, for example `getSellerInsights(days = 30)`.

The UI should match the existing Element Plus style and keep the page useful when the insight request is loading or unavailable.

## Reliability And Security

- Keep `OPENAI_API_KEY` server-side only.
- Never commit `.env` or real credentials.
- Add `.env.example` if the repo does not already document environment variables.
- Bound the analysis window to prevent expensive queries.
- Add a model-call timeout.
- Validate model output before sending it to the frontend.
- Return fallback output with the same schema.
- Include `meta.source` so the demo can explain whether the output came from OpenAI or local rules.

## Testing Strategy

Backend tests should cover:

- Metric aggregation for a seller with orders, order items, and products.
- Empty data in the selected 30-day window.
- Fallback output shape and priority assignment.
- Missing `OPENAI_API_KEY` uses fallback.
- Simulated OpenAI exception uses fallback.
- Invalid model JSON uses fallback.
- API endpoint returns the expected schema.

Frontend verification should cover:

- Loading state.
- Briefing and card rendering.
- Fallback badge rendering.
- Empty-data state.
- Existing sales page content still remains available below the AI panel.

## Interview Narrative

This feature should be presented as a realistic FDE engagement:

1. The legacy system already supports seller products, orders, and sales charts.
2. The seller pain is not data absence; it is translating operational data into decisions.
3. The FDE adds an AI layer at the workflow point where sellers already review performance.
4. The backend computes trustworthy structured facts first, then asks the model to explain and prioritize.
5. The design protects reliability through schema validation and deterministic fallback.
6. The demo remains stable without an API key but can use a real model when configured.

This makes the portfolio stronger than a generic chatbot because it shows product judgment, backend integration, model-boundary design, and operational reliability.

## Out Of Scope For This Iteration

- Buyer-facing shopping assistant.
- Chat-based seller analyst.
- Persistent insight history table.
- Prompt version registry.
- Scheduled weekly report generation.
- Sending messages to buyers.
- Admin-level analytics across all sellers.

These can be mentioned as future roadmap items after the core feature works.
