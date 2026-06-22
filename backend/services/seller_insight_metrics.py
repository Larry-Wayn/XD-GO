from collections import defaultdict
from datetime import datetime, timedelta

from backend.models import Order, OrderItem, Product

ALLOWED_INSIGHT_DAYS = {7, 30, 90}
FULFILLED_STATUSES = {"shipped", "delivered"}
ORDER_STATUSES = ("unpaid", "pending", "shipped", "delivered")


def parse_insight_days(value):
    try:
        days = int(value)
    except (TypeError, ValueError):
        return 30
    return days if days in ALLOWED_INSIGHT_DAYS else 30


def _as_float(value):
    return round(float(value or 0), 2)


def _date_string(value):
    return value.strftime("%Y-%m-%d")


def get_seller_insight_metrics(seller_id, days=30, now=None):
    window_days = parse_insight_days(days)
    end_date = now or datetime.utcnow()
    start_date = end_date - timedelta(days=window_days)

    products = Product.query.filter_by(userid=seller_id).all()
    product_map = {product.proid: product for product in products}

    orders = Order.query.filter(
        Order.sellerid == seller_id,
        Order.createtime >= start_date,
        Order.createtime <= end_date
    ).all()
    order_map = {order.orderid: order for order in orders}
    order_ids = list(order_map)

    order_items = []
    if order_ids:
        order_items = OrderItem.query.filter(OrderItem.orderid.in_(order_ids)).all()

    status_breakdown = {status: 0 for status in ORDER_STATUSES}
    for order in orders:
        status_breakdown[order.status] = status_breakdown.get(order.status, 0) + 1

    fulfilled_order_ids = {
        order.orderid for order in orders if order.status in FULFILLED_STATUSES
    }

    sold_by_product = defaultdict(int)
    revenue_by_product = defaultdict(float)
    product_name_by_id = {}

    for item in order_items:
        product = product_map.get(item.proid)
        product_name_by_id[item.proid] = product.name if product else item.productname
        if item.orderid not in fulfilled_order_ids:
            continue
        quantity = int(item.quantity or 0)
        item_revenue = _as_float(item.price) * quantity
        sold_by_product[item.proid] += quantity
        revenue_by_product[item.proid] += item_revenue

    revenue = round(sum(revenue_by_product.values()), 2)

    top_products = []
    for product_id, product_revenue in sorted(
        revenue_by_product.items(), key=lambda pair: pair[1], reverse=True
    )[:5]:
        product = product_map.get(product_id)
        top_products.append({
            "productId": product_id,
            "productName": product_name_by_id.get(product_id) or product_id,
            "quantitySold": sold_by_product.get(product_id, 0),
            "revenue": round(product_revenue, 2),
            "stock": int(product.stock) if product else 0
        })

    low_stock_products = []
    slow_moving_products = []
    for product in products:
        sold_quantity = sold_by_product.get(product.proid, 0)
        stock = int(product.stock or 0)
        product_data = {
            "productId": product.proid,
            "productName": product.name,
            "stock": stock,
            "quantitySold": sold_quantity
        }
        if stock <= 5 or (sold_quantity > 0 and stock <= sold_quantity):
            low_stock_products.append(product_data)
        if stock >= 20 and sold_quantity == 0:
            slow_moving_products.append(product_data)

    top_three_revenue = sum(item["revenue"] for item in top_products[:3])
    revenue_concentration = round(top_three_revenue / revenue, 4) if revenue else 0

    return {
        "windowDays": window_days,
        "startDate": _date_string(start_date),
        "endDate": _date_string(end_date),
        "orderCount": len(orders),
        "revenue": revenue,
        "pendingOrders": status_breakdown.get("pending", 0),
        "statusBreakdown": status_breakdown,
        "topProducts": top_products,
        "lowStockProducts": low_stock_products[:5],
        "slowMovingProducts": slow_moving_products[:5],
        "revenueConcentration": revenue_concentration
    }
