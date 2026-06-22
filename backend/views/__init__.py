from flask import Blueprint
from .auth import main as auth_blueprint
from .buyer_cart import main as buyer_cart_blueprint
from .buyer_order import main as buyer_order_blueprint
from .product import main as product_blueprint
from .seller import main as seller_blueprint
from .seller_insights import main as seller_insights_blueprint
from .user import main as user_blueprint
from .common import main as common_blueprint


def register_blueprints(app):
    app.register_blueprint(auth_blueprint, url_prefix='/api/auth')
    app.register_blueprint(buyer_cart_blueprint, url_prefix='/api/cart')
    app.register_blueprint(buyer_order_blueprint, url_prefix='/api/buy_order')
    app.register_blueprint(product_blueprint, url_prefix='/api/product')
    app.register_blueprint(seller_blueprint, url_prefix='/api/sell_order')
    app.register_blueprint(seller_insights_blueprint, url_prefix='/api/sell_order')
    app.register_blueprint(user_blueprint, url_prefix='/api/users')
    app.register_blueprint(common_blueprint, url_prefix='')
