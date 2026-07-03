from decimal import Decimal

import jwt
import pytest
from flask import Flask

from backend import db
from backend.models import Cart, CartItem, Category, Order, OrderItem, Product, User
from backend.views.buyer_cart import main as buyer_cart_blueprint
from backend.views.buyer_order import main as buyer_order_blueprint


@pytest.fixture
def app():
    test_app = Flask(__name__)
    test_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(test_app)
    test_app.register_blueprint(buyer_cart_blueprint, url_prefix='/api/cart')
    test_app.register_blueprint(buyer_order_blueprint, url_prefix='/api/buy_order')

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _token(user_id):
    return jwt.encode({'userid': user_id}, 'your_secret_key', algorithm='HS256')


def _auth_headers(user_id='buyer_1'):
    return {'Authorization': f'Bearer {_token(user_id)}'}


def _seed_cart(quantity=2, stock=10):
    buyer = User(
        userid='buyer_1',
        username='buyer',
        password='pw',
        email='buyer@example.com',
        role='buyer',
    )
    seller = User(
        userid='seller_1',
        username='seller',
        password='pw',
        email='seller@example.com',
        role='seller',
    )
    category = Category(catid='cat_1', name='Electronics')
    product = Product(
        proid='pro_1',
        name='Keyboard',
        price=Decimal('100.00'),
        stock=stock,
        description='Mechanical keyboard',
        catid='cat_1',
        userid='seller_1',
        image='keyboard.png',
    )
    cart = Cart(carid='cart_1', userid='buyer_1')
    cart_item = CartItem(carid='cart_1', proid='pro_1', quantity=quantity)
    db.session.add_all([buyer, seller, category, product, cart, cart_item])
    db.session.commit()


def _add_second_cart_item(quantity=1, stock=5):
    product = Product(
        proid='pro_2',
        name='Mouse',
        price=Decimal('50.00'),
        stock=stock,
        description='Wireless mouse',
        catid='cat_1',
        userid='seller_1',
        image='mouse.png',
    )
    cart_item = CartItem(carid='cart_1', proid='pro_2', quantity=quantity)
    db.session.add_all([product, cart_item])
    db.session.commit()


def test_update_cart_quantity_accepts_frontend_proid_payload(app, client):
    with app.app_context():
        _seed_cart(quantity=1, stock=8)

    response = client.post(
        '/api/cart/update_quantity',
        json={'proid': 'pro_1', 'quantity': 3},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert response.get_json()['code'] == 200
    with app.app_context():
        cart_item = CartItem.query.filter_by(carid='cart_1', proid='pro_1').first()
        assert cart_item.quantity == 3


def test_get_cart_list_returns_empty_products_for_new_buyer(app, client):
    with app.app_context():
        db.session.add(User(
            userid='buyer_1',
            username='buyer',
            password='pw',
            email='buyer@example.com',
            role='buyer',
        ))
        db.session.commit()

    response = client.get('/api/cart/list', headers=_auth_headers())

    body = response.get_json()
    assert response.status_code == 200
    assert body['code'] == 200
    assert body['data']['products'] == []


def test_submit_order_returns_frontend_compatible_order_payload(app, client):
    with app.app_context():
        _seed_cart(quantity=2, stock=8)

    response = client.post(
        '/api/buy_order/submit',
        json={
            'addressId': 1,
            'paymentMethod': 'alipay',
            'items': [{'productId': 'pro_1', 'quantity': 2}],
        },
        headers=_auth_headers(),
    )

    body = response.get_json()

    assert response.status_code == 200
    assert body['code'] == 200
    assert isinstance(body['data'], dict)
    assert body['data']['order_no']
    assert body['data']['orders'][0]['orderid'] == body['data']['order_no']
    assert body['data']['orders'][0]['status'] == 'pending'
    with app.app_context():
        order = Order.query.filter_by(orderid=body['data']['order_no']).first()
        assert order is not None
        assert order.totalprice == Decimal('200.00')
        assert db.session.get(Product, 'pro_1').stock == 6
        assert CartItem.query.filter_by(carid='cart_1').count() == 0


def test_submit_order_only_processes_selected_frontend_items(app, client):
    with app.app_context():
        _seed_cart(quantity=2, stock=8)
        _add_second_cart_item(quantity=1, stock=5)

    response = client.post(
        '/api/buy_order/submit',
        json={
            'items': [{'productId': 'pro_1', 'quantity': 2}],
        },
        headers=_auth_headers(),
    )

    body = response.get_json()

    assert response.status_code == 200
    assert body['data']['order_no']
    with app.app_context():
        order_items = OrderItem.query.filter_by(orderid=body['data']['order_no']).all()
        assert [item.proid for item in order_items] == ['pro_1']
        assert db.session.get(Product, 'pro_1').stock == 6
        assert db.session.get(Product, 'pro_2').stock == 5
        remaining_cart_item = CartItem.query.filter_by(carid='cart_1', proid='pro_2').first()
        assert remaining_cart_item is not None
        assert remaining_cart_item.quantity == 1


def test_web_pay_reuses_submitted_order_no(app, client, monkeypatch):
    captured = {}

    class FakeAlipay:
        def api_alipay_trade_page_pay(self, **kwargs):
            captured.update(kwargs)
            return 'signed_payment_query=1'

    monkeypatch.setattr(
        'backend.views.buyer_order.alipay_obj',
        lambda: FakeAlipay(),
    )

    with app.app_context():
        _seed_cart()
        db.session.add(Order(
            orderid='order_123',
            userid='buyer_1',
            sellerid='seller_1',
            status='pending',
            totalprice=Decimal('200.00'),
        ))
        db.session.commit()

    response = client.post(
        '/api/buy_order/pay',
        json={
            'order_no': 'order_123',
            'total_amount': '200.00',
            'subject': '订单支付-order_123',
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert captured['out_trade_no'] == 'order_123'
    assert response.get_json()['pay_url'].endswith('signed_payment_query=1')
