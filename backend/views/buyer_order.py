from flask import Blueprint, jsonify,request,url_for,redirect
from backend.models import db, Product, Cart, CartItem, Order, OrderItem
from backend.views.auth import token_required
from .pay import alipay_obj
import uuid
from flask import request
import pprint
from decimal import Decimal, InvalidOperation

main = Blueprint('buyer_order', __name__)
temp_orders = {}


def _selected_cart_quantities(payload):
    items = payload.get('items') if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items:
        return None

    quantities = {}
    for item in items:
        if not isinstance(item, dict):
            return {}
        product_id = item.get('productId') or item.get('proid') or item.get('id')
        try:
            quantity = int(item.get('quantity', 0))
        except (TypeError, ValueError):
            return {}
        if not product_id or quantity <= 0:
            return {}
        quantities[str(product_id)] = quantity
    return quantities

# 支付接口模拟函数，仅供参考
def initiate_payment(order_id, totalprice):
    # This function would interact with a payment gateway like PayPal, Stripe, etc.
    # For now, we simulate a successful payment process
    # Here you would send a request to a payment gateway API, then return success/failure status

    # Example (mocked) payment status: returning success directly.
    return "success"


# 买家获取订单列表与详情API[GET]    /api/buy_order/list
@main.route('/list', methods=['GET'])
@token_required
def get_order_list(current_user):
    try:
        # Ensure the user is a buyer
        if current_user.role != 'buyer':
            return jsonify({
                "code": 403,
                "message": "Access denied: Only buyers can view their orders"
            }), 403

        # Get the user's orders
        orders = Order.query.filter_by(userid=current_user.userid).order_by(Order.createtime.desc()).all()
        if not orders:
            return jsonify({
                "code": 404,
                "message": "No orders found"
            }), 404

        # Get the order details for each order
        order_list = []
        for order in orders:
            order_items = OrderItem.query.filter_by(orderid=order.orderid).all()
            order_items_data = []
            for item in order_items:
                product = Product.query.filter_by(proid=item.proid).first()
                if not product:
                    return jsonify({
                        "code": 0,
                        "message": f"Product not found: {item.proid}"
                    }), 404

                order_items_data.append({
                    "proid": product.proid,
                    "name": product.name,
                    "price": str(product.price),
                    "quantity": item.quantity,
                    "image": product.image
                })

            order_list.append({
                "orderid": order.orderid,
                "totalprice": str(order.totalprice),
                "status": order.status,
                "createtime": order.createtime.strftime("%Y-%m-%d %H:%M:%S"),
                "order_items": order_items_data
            })

        pprint.pprint(order_list)  # Debugging line to print the order list

        # Return the order list
        return jsonify({
            "code": 200,
            "message": "Order list retrieved successfully",
            "data": {
                "orders": order_list
            }
        }), 200  # OK

    except Exception as e:
        print(e)
        return jsonify({
            "code": 0,
            "message": f"Error: {str(e)}"
        }), 500  # Internal Server Error


# 买家创建订单发送给卖家API[POST]   /api/buy_order/submit
@main.route('/submit', methods=['POST'])
@token_required
def submit_order(current_user):
    try:
        # 确保用户是买家
        if current_user.role != 'buyer':
            return jsonify({
                "code": 403,
                "message": "Access denied: Only buyers can submit orders"
            }), 403

        data = request.get_json(silent=True) or {}

        # 获取购物车信息
        cart = Cart.query.filter_by(userid=current_user.userid).first()
        if not cart:
            return jsonify({
                "code": 400,
                "message": "Cart is empty"
            }), 400

        cart_items = CartItem.query.filter_by(carid=cart.carid).all()
        if not cart_items:
            return jsonify({
                "code": 400,
                "message": "No items in the cart"
            }), 400

        selected_quantities = _selected_cart_quantities(data)
        if selected_quantities == {}:
            return jsonify({
                "code": 400,
                "message": "Invalid input: items must include productId and positive quantity"
            }), 400
        if selected_quantities is not None:
            cart_items = [
                item for item in cart_items
                if item.proid in selected_quantities
            ]
            if not cart_items:
                return jsonify({
                    "code": 400,
                    "message": "Selected products are not in the cart"
                }), 400

        # 按卖家分组商品
        grouped_items = {}
        for item in cart_items:
            product = Product.query.filter_by(proid=item.proid).first()
            if not product:
                return jsonify({
                    "code": 404,
                    "message": f"Product not found: {item.proid}"
                }), 404

            quantity = selected_quantities.get(item.proid, item.quantity) if selected_quantities is not None else item.quantity
            if quantity > product.stock:
                return jsonify({
                    "code": 400,
                    "message": f"Insufficient stock for product: {product.name}"
                }), 400

            if product.userid not in grouped_items:
                grouped_items[product.userid] = []
            grouped_items[product.userid].append((item, product, quantity))

        # 处理每个卖家的订单
        payment_results = []
        for seller_id, items in grouped_items.items():
            order_id = str(uuid.uuid4())
            totalprice = 0
            order_items = []
            cart_item_ids = []  # 记录该订单对应的购物车项 ID

            # 在内存中准备订单项
            for cart_item, product, quantity in items:
                totalprice += product.price * quantity
                order_items.append(OrderItem(
                    orderid=order_id,
                    proid=product.proid,
                    productname=product.name,
                    price=product.price,
                    quantity=quantity
                ))
                cart_item_ids.append(cart_item.id)

            # 模拟支付接口
            payment_status = initiate_payment(order_id, totalprice)
            if payment_status == "success":
                # 支付成功，创建并保存订单
                order = Order(
                    orderid=order_id,
                    userid=current_user.userid,
                    sellerid=seller_id,
                    status='pending',  # 支付成功直接设为 pending
                    totalprice=totalprice
                )
                db.session.add(order)
                db.session.add_all(order_items)
                # 减少库存
                for cart_item, product, quantity in items:
                    product.stock -= quantity
                # 删除该订单对应的购物车项
                CartItem.query.filter(CartItem.id.in_(cart_item_ids)).delete(synchronize_session=False)
                db.session.commit()
                payment_results.append({
                    "orderid": order_id,
                    "totalprice": str(totalprice),
                    "status": "pending"
                })
            else:
                # 支付失败，不保存订单
                payment_results.append({
                    "orderid": order_id,
                    "totalprice": str(totalprice),
                    "status": "cancelled"
                })

        first_order_no = payment_results[0]["orderid"] if payment_results else ""

        return jsonify({
            "code": 200,
            "message": "Order submission complete",
            "data": {
                "order_no": first_order_no,
                "orders": payment_results
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        print("Error: ", e)
        return jsonify({
            "code": 500,
            "message": f"Server error: {str(e)}"
        }), 500


# 买家确认收货接口[PUT]   /api/buy_order/confirm_delivery
@main.route('/confirm_delivery', methods=['PUT'])
@token_required
def confirm_delivery(current_user):
    try:
        # 确保用户是买家
        if current_user.role != 'buyer':
            return jsonify({
                "code": 403,
                "message": "Access denied: Only buyers can confirm delivery"
            }), 403

        # 获取前端发送的请求数据
        data = request.get_json()
        if not data or 'orderid' not in data:
            return jsonify({
                "code": 400,
                "message": "Invalid input: Missing required field 'orderid'"
            }), 400

        # 检查订单是否存在
        order = Order.query.filter_by(orderid=data['orderid']).first()
        if not order:
            return jsonify({
                "code": 404,
                "message": f"Order not found with orderid: {data['orderid']}"
            }), 404

        # 检查订单是否属于当前买家
        if order.userid != current_user.userid:
            return jsonify({
                "code": 403,
                "message": "Access denied: Order does not belong to you"
            }), 403

        # 检查订单当前状态是否为 "shipped"
        if order.status != 'shipped':
            return jsonify({
                "code": 400,
                "message": "Order status can only be updated to 'delivered' from 'shipped'"
            }), 400

        # 更新订单状态为 "delivered"
        order.status = 'delivered'
        db.session.commit()

        return jsonify({
            "code": 200,
            "message": "Order status updated to 'delivered' successfully",
            "data": {
                "orderid": data['orderid'],
                "status": order.status
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        print(e)
        return jsonify({
            "code": 500,
            "message": f"Error: {str(e)}"
        }), 500


@main.route('/pay', methods=['POST'])
@token_required
def web_pay(current_user):
    """电脑网站支付"""
    data = request.get_json(silent=True) or {}
    order_no = data.get('order_no') or str(uuid.uuid4())
    total_amount = data.get('total_amount')
    subject = data.get('subject') or f"订单支付-{order_no}"

    order = Order.query.filter_by(orderid=order_no, userid=current_user.userid).first()
    if order:
        total_amount = total_amount or str(order.totalprice)
    elif data.get('order_no'):
        return jsonify({
            "status": 0,
            "message": f"Order not found with order_no: {order_no}"
        }), 404

    try:
        Decimal(str(total_amount))
    except (InvalidOperation, TypeError, ValueError):
        return jsonify({
            "status": 0,
            "message": "Invalid input: total_amount is required"
        }), 400

    alipay = alipay_obj()
    order_string = alipay.api_alipay_trade_page_pay(
        out_trade_no=order_no,
        total_amount=total_amount,
        subject=subject,
        return_url=url_for('buyer_order.alipay_success_result', _external=True),
        notify_url=url_for('buyer_order.alipay_notify', _external=True)
    )

    pay_url = f"https://openapi-sandbox.dl.alipaydev.com/gateway.do?{order_string}"
    return jsonify({'status': 1, 'pay_url': pay_url})

@main.route('/check_pay', methods=['POST'])
def check_pay():
    order_no = request.form.get('order_no')
    order_status = temp_orders.get(order_no, {'paid': False})
    
    try:
        response = alipay_obj().api_alipay_trade_query(out_trade_no=order_no)
        if response.get('trade_status') in ('TRADE_SUCCESS', 'TRADE_FINISHED'):
            temp_orders[order_no]['paid'] = True
    except Exception as e:
        pass
    
    return jsonify({'paid': order_status['paid']})

@main.route('/alipay/notify', methods=['POST'])
def alipay_notify():
    data = request.form.to_dict()
    signature = data.pop('sign', '')

    if alipay_obj().verify(data, signature):
        trade_status = data.get('trade_status')
        order_no = data.get('out_trade_no')
        
        if trade_status in ('TRADE_SUCCESS', 'TRADE_FINISHED'):
            # 更新数据库订单状态
            order = Order.query.filter_by(orderid=order_no).first()
            if order:
                order.status = 'paid'
                db.session.commit()
            return 'success'
    
    return 'fail'

# 支付宝同步通知接口（支付成功后跳转）
@main.route('/alipay/return')
def alipay_success_result():
    return redirect(f"http://localhost:5173/order")
