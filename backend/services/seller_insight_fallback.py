from backend.services.seller_insight_schema import build_insight_payload


def _money(value):
    return f"¥{float(value or 0):.2f}"


def _priority_for_pending(pending_orders, order_count):
    if pending_orders >= 5 or (order_count and pending_orders / order_count >= 0.3):
        return "high"
    return "medium"


def build_fallback_insight(metrics, knowledge_sources=None):
    window_days = metrics.get("windowDays", 30)
    order_count = metrics.get("orderCount", 0)
    revenue = metrics.get("revenue", 0)
    pending_orders = metrics.get("pendingOrders", 0)
    top_products = metrics.get("topProducts", [])
    low_stock_products = metrics.get("lowStockProducts", [])
    slow_moving_products = metrics.get("slowMovingProducts", [])
    revenue_concentration = metrics.get("revenueConcentration", 0)

    if order_count == 0:
        return build_insight_payload(
            f"近{window_days}天暂无订单数据。建议先检查商品曝光、价格和库存状态，再结合后续订单变化复盘运营效果。",
            [{
                "title": "先积累可分析的订单样本",
                "priority": "low",
                "recommendation": "保持商品信息完整，并在产生订单后重新查看 AI 运营洞察。",
                "reason": "当前时间窗口内没有订单，无法判断销量趋势或库存风险。",
                "evidence": [f"近{window_days}天订单数: 0"],
                "metric": "order_count"
            }],
            metrics,
            "fallback"
        )

    cards = []
    if pending_orders:
        cards.append({
            "title": "优先处理待发货订单",
            "priority": _priority_for_pending(pending_orders, order_count),
            "recommendation": "今天优先处理待发货订单，降低履约延迟和买家体验风险。",
            "reason": "待发货订单会直接影响履约体验，是最短路径的运营动作。",
            "evidence": [f"待发货订单: {pending_orders}", f"近{window_days}天订单: {order_count}"],
            "metric": "pending_orders"
        })

    for product in low_stock_products[:2]:
        cards.append({
            "title": f"补货: {product['productName']}",
            "priority": "high" if product["stock"] <= 3 else "medium",
            "recommendation": "尽快确认库存或下架风险商品，避免热销商品缺货影响收入。",
            "reason": "该商品库存偏低，且近期已有销量信号。",
            "evidence": [f"当前库存: {product['stock']}", f"近{window_days}天销量: {product['quantitySold']}"],
            "metric": "low_stock"
        })

    for product in slow_moving_products[:2]:
        cards.append({
            "title": f"促活滞销品: {product['productName']}",
            "priority": "medium",
            "recommendation": "考虑优化标题描述、调整价格或搭配热销商品做促销。",
            "reason": "该商品库存较高但近期没有形成销量。",
            "evidence": [f"当前库存: {product['stock']}", f"近{window_days}天销量: {product['quantitySold']}"],
            "metric": "slow_moving"
        })

    if revenue_concentration >= 0.65 and top_products:
        cards.append({
            "title": "保护核心收入商品",
            "priority": "medium",
            "recommendation": "重点保障 Top 商品库存和履约质量，同时寻找第二增长点。",
            "reason": "收入集中度较高，核心商品波动会明显影响店铺表现。",
            "evidence": [f"Top3 收入占比: {revenue_concentration:.0%}", f"第一商品: {top_products[0]['productName']}"],
            "metric": "revenue_concentration"
        })

    if not cards:
        cards.append({
            "title": "保持当前运营节奏",
            "priority": "low",
            "recommendation": "继续观察订单状态和热销商品变化，优先保证商品信息与库存准确。",
            "reason": "当前没有明显的履约、库存或滞销风险。",
            "evidence": [f"近{window_days}天订单: {order_count}", f"收入: {_money(revenue)}"],
            "metric": "general"
        })

    top_product_text = "暂无明显热销商品"
    if top_products:
        top = top_products[0]
        top_product_text = f"热销商品为 {top['productName']}，贡献收入 {_money(top['revenue'])}"

    briefing = (
        f"近{window_days}天店铺共产生 {order_count} 个订单，已发货/已完成订单收入为 {_money(revenue)}。"
        f"{top_product_text}。当前待发货订单 {pending_orders} 个，"
        f"低库存商品 {len(low_stock_products)} 个，滞销风险商品 {len(slow_moving_products)} 个。"
        "建议优先处理履约和库存动作，再针对滞销商品做商品页或价格优化。"
    )
    return build_insight_payload(briefing, cards, metrics, "fallback")
