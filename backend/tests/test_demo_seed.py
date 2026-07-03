from flask import Flask

from backend import db
from backend.models import Category, Order, OrderItem, Product, User
from backend.services.demo_seed import (
    DEMO_BUYER_ID,
    DEMO_BUYER_USERNAME,
    DEMO_SELLERS,
    seed_multiseller_demo_data,
)


def _create_test_app():
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(app)
    return app


def test_seed_multiseller_demo_data_gives_every_seller_orders():
    app = _create_test_app()
    with app.app_context():
        db.create_all()

        summary = seed_multiseller_demo_data()

        assert summary['buyer_id'] == DEMO_BUYER_ID
        assert summary['seller_count'] == len(DEMO_SELLERS)
        buyer = User.query.filter_by(userid=DEMO_BUYER_ID, role='buyer').first()
        assert buyer
        assert buyer.username == DEMO_BUYER_USERNAME
        assert ' ' not in buyer.username

        for seller in DEMO_SELLERS:
            seller_id = seller['userid']
            seller_user = db.session.get(User, seller_id)
            assert seller_user.username == seller['username']
            assert ' ' not in seller_user.username
            assert Product.query.filter_by(userid=seller_id).count() >= 1

            seller_orders = Order.query.filter_by(sellerid=seller_id).all()
            assert len(seller_orders) == 1
            assert seller_orders[0].userid == DEMO_BUYER_ID
            assert seller_orders[0].totalprice > 0

            order_items = OrderItem.query.filter_by(orderid=seller_orders[0].orderid).all()
            assert order_items
            for item in order_items:
                product = db.session.get(Product, item.proid)
                assert product.userid == seller_id

        category_names = {category.name for category in Category.query.all()}
        assert {'Electronics', 'Clothing', 'Home Appliances'}.issubset(category_names)
        assert all(not name.startswith('Demo ') for name in category_names)

        db.session.remove()
        db.drop_all()


def test_seed_multiseller_demo_data_is_idempotent():
    app = _create_test_app()
    with app.app_context():
        db.create_all()

        seed_multiseller_demo_data()
        seed_multiseller_demo_data()

        assert Order.query.count() == len(DEMO_SELLERS)
        assert User.query.filter_by(role='seller').count() == len(DEMO_SELLERS)

        order_ids = [order.orderid for order in Order.query.all()]
        assert len(order_ids) == len(set(order_ids))

        db.session.remove()
        db.drop_all()


def test_seed_multiseller_demo_data_removes_legacy_demo_categories():
    app = _create_test_app()
    with app.app_context():
        db.create_all()
        db.session.add_all([
            Category(catid='demo_cat_fashion', name='Demo Fashion'),
            Product(
                proid='legacy_demo_product',
                name='Legacy Demo Product',
                price=10,
                stock=1,
                description='legacy',
                catid='demo_cat_fashion',
                userid=None,
            )
        ])
        db.session.commit()

        seed_multiseller_demo_data()

        assert Category.query.filter_by(catid='demo_cat_fashion').first() is None
        legacy_product = db.session.get(Product, 'legacy_demo_product')
        assert legacy_product.catid == 'cat_clothing'

        db.session.remove()
        db.drop_all()
