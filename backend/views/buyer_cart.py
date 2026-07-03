import uuid
from flask import Blueprint, request, jsonify
from backend.models import Cart, CartItem, Product
from backend.views.auth import token_required
from backend import db

main = Blueprint('buyer_cart', __name__)


# 买家添加商品到购物车API[PUT]  /api/cart/add_product
@main.route('/add_product', methods=['PUT'])
@token_required
def add_product_to_cart(current_user):
    try:
        # Ensure the user is a buyer
        if current_user.role != 'buyer':
            return jsonify({
                "code": 403,
                "message": "Access denied: Only buyers can add products to cart"
            }), 403

        # Get the product ID and quantity from the request
        data = request.get_json()
        if not data or 'proid' not in data or 'quantity' not in data:
            return jsonify({
                "code": 400,
                "message": "Invalid input: Missing required fields 'proid' and 'quantity'"
            }), 400

        # Check if the product exists
        product = Product.query.filter_by(proid=data['proid']).first()
        if not product:
            return jsonify({
                "code": 404,
                "message": f"Product not found with proid: {data['proid']}"
            }), 404

        # Get the cart for the user (if it doesn't exist, create one)
        cart = Cart.query.filter_by(userid=current_user.userid).first()
        if not cart:
            cart = Cart(
                carid=str(uuid.uuid4()),
                userid=current_user.userid
            )
            db.session.add(cart)
            db.session.commit()

        # Check if the user already has the product in their cart
        cart_item = CartItem.query.filter_by(carid=cart.carid, proid=data['proid']).first()
        if cart_item:
            # Update the quantity if the product is already in the cart
            cart_item.quantity += data['quantity']
            db.session.commit()
        else:
            # Add the product to the cart if it's not already there
            cart_item = CartItem(
                carid=cart.carid,
                proid=data['proid'],
                quantity=data['quantity']
            )
            db.session.add(cart_item)
            db.session.commit()

        return jsonify({
            "code": 200,
            "message": "Product added to cart successfully",
            "data": {
                "proid": data['proid'],
                "quantity": data['quantity']
            }
        }), 200  # OK

    except Exception as e:
        print(f"Error: {str(e)}")
        db.session.rollback()
        return jsonify({
            "code": 500,
            "message": f"Error: {str(e)}"
        }), 500  # Internal Server Error


# 买家获取购物车列表API[GET]   /api/cart/list
@main.route('/list', methods=['GET'])
@token_required
def get_cart_list(current_user):
    try:
        # Ensure the user is a buyer
        if current_user.role != 'buyer':
            return jsonify({
                "code": 0,
                "message": "Access denied: Only buyers can view their cart"
            }), 403

        # Get the user's cart
        cart = Cart.query.filter_by(userid=current_user.userid).first()
        if not cart:
            return jsonify({
                "code": 200,
                "message": "Cart is empty",
                "data": {
                    "products": []
                }
            }), 200

        # Get the cart items
        cart_items = CartItem.query.filter_by(carid=cart.carid).all()
        if not cart_items:
            return jsonify({
                "code": 200,
                "message": "Cart is empty",
                "data": {
                    "products": []
                }
            }), 200

        # Get the product details for each item
        products = []
        for item in cart_items:
            product = Product.query.filter_by(proid=item.proid).first()
            if not product:
                return jsonify({
                    "code": 0,
                    "message": f"Product not found: {item.proid}"
                }), 404

            products.append({
                "proid": product.proid,
                "name": product.name,
                "price": str(product.price),
                "quantity": item.quantity,
                "image": product.image
            })

        # Return the cart list
        return jsonify({
            "code": 200,
            "message": "Cart list retrieved successfully",
            "data": {
                "products": products
            }
        }), 200  # OK

    except Exception as e:
        return jsonify({
            "code": 0,
            "message": f"Error: {str(e)}"
        }), 500  # Internal Server Error


# 买家删除购物车商品API[DELETE]   /api/cart/remove_product
@main.route('/remove_product', methods=['DELETE'])
@token_required
def remove_product_from_cart(current_user):
    try:
        if current_user.role != 'buyer':
            return jsonify({
                "code": 403,
                "message": "只有买家可以从购物车移除商品"
            }), 403

        data = request.get_json()
        proid = data.get('ids')
        print(proid, "is being removed from cart")
        if not proid:
            print(data)
            return jsonify({
                "code": 400,
                "message": "缺少必要参数: proid或ids"
            }), 400

        cart = Cart.query.filter_by(userid=current_user.userid).first()
        if not cart:
            return jsonify({
                "code": 404,
                "message": "购物车不存在"
            }), 404

        cart_item = CartItem.query.filter_by(carid=cart.carid, proid=str(proid)).first()
        print(cart_item, "is being removed from cart")
        if not cart_item:
            return jsonify({
                "code": 404,
                "message": "商品不在购物车中"
            }), 404

        db.session.delete(cart_item)
        db.session.commit()

        return jsonify({
            "code": 200,
            "message": "商品已从购物车移除",
            "data": {
                "proid": proid
            }
        }), 200

    except Exception as e:
        print(e)
        return jsonify({
            "code": 500,
            "message": f"服务器错误: {str(e)}"
        }), 500


# 买家修改购物车商品数量API[POST]   /api/cart/update_quantity
@main.route('/update_quantity', methods=['POST'])
@token_required
def update_cart_item_quantity(current_user):
    try:
        if current_user.role != 'buyer':
            print("Only buyers can update cart item quantity")
            return jsonify({
                "code": 403,
                "message": "只有买家可以修改购物车商品数量"
            }), 403

        data = request.get_json()
        if not data or 'proid' not in data or 'quantity' not in data:
            print("缺少必要参数", data)
            return jsonify({
                "code": 400,
                "message": "缺少必要参数: proid 或 quantity"
            }), 400

        product = Product.query.filter_by(proid=data['proid']).first()
        if not product:
            return jsonify({
                "code": 404,
                "message": f"未找到商品: {data['proid']}"
            }), 404

        if data['quantity'] <= 0:
            return jsonify({
                "code": 400,
                "message": "数量必须大于0"
            }), 400

        if product.stock < data['quantity']:
            return jsonify({
                "code": 400,
                "message": "库存不足",
                "available_stock": product.stock
            }), 400

        cart = Cart.query.filter_by(userid=current_user.userid).first()
        if not cart:
            return jsonify({
                "code": 404,
                "message": "购物车不存在"
            }), 404

        cart_item = CartItem.query.filter_by(carid=cart.carid, proid=data['proid']).first()
        if not cart_item:
            return jsonify({
                "code": 404,
                "message": "商品不在购物车中"
            }), 404

        cart_item.quantity = data['quantity']
        db.session.commit()

        return jsonify({
            "code": 200,
            "message": "购物车商品数量已更新",
            "data": {
                "proid": data['proid'],
                "quantity": data['quantity']
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        print(e)
        return jsonify({
            "code": 500,
            "message": f"服务器错误: {str(e)}"
        }), 500


# 买家清空购物车API[DELETE]   /api/cart/clear
@main.route('/clear', methods=['DELETE'])
@token_required
def clear_cart(current_user):
    try:
        if current_user.role != 'buyer':
            return jsonify({
                "code": 403,
                "message": "只有买家可以清空购物车"
            }), 403

        cart = Cart.query.filter_by(userid=current_user.userid).first()
        if not cart:
            return jsonify({
                "code": 404,
                "message": "购物车不存在"
            }), 404

        CartItem.query.filter_by(carid=cart.carid).delete()
        db.session.commit()

        return jsonify({
            "code": 200,
            "message": "购物车已清空"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "code": 500,
            "message": f"服务器错误: {str(e)}"
        }), 500
