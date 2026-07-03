from decimal import Decimal

from backend import db
from backend.models import Category, Order, OrderItem, Product, User

DEMO_BUYER_ID = 'buyer_demo_multi'
DEMO_BUYER_USERNAME = 'demo_buyer_multi'

DEMO_SELLERS = [
    {
        'userid': 'seller_demo_electronics',
        'username': 'demo_seller_electronics',
        'password': 'seller123',
        'email': 'seller.electronics@example.com',
        'phone': '18800000001',
    },
    {
        'userid': 'seller_demo_fashion',
        'username': 'demo_seller_fashion',
        'password': 'seller123',
        'email': 'seller.fashion@example.com',
        'phone': '18800000002',
    },
    {
        'userid': 'seller_demo_home',
        'username': 'demo_seller_home',
        'password': 'seller123',
        'email': 'seller.home@example.com',
        'phone': '18800000003',
    },
]

DEMO_CATEGORIES = [
    {'catid': 'cat_electronics', 'name': 'Electronics'},
    {'catid': 'cat_clothing', 'name': 'Clothing'},
    {'catid': 'cat_home_appliances', 'name': 'Home Appliances'},
]

LEGACY_DEMO_CATEGORY_MAP = {
    'demo_cat_electronics': 'cat_electronics',
    'demo_cat_fashion': 'cat_clothing',
    'demo_cat_home': 'cat_home_appliances',
}

DEMO_PRODUCTS = [
    {
        'proid': 'demo_pro_keyboard',
        'name': 'AI Keyboard',
        'price': Decimal('199.00'),
        'stock': 40,
        'description': 'Wireless keyboard for seller demo.',
        'catid': 'cat_electronics',
        'userid': 'seller_demo_electronics',
        'image': 'https://picsum.photos/seed/demo-keyboard/600/600',
    },
    {
        'proid': 'demo_pro_headphones',
        'name': 'Noise Cancelling Headphones',
        'price': Decimal('399.00'),
        'stock': 24,
        'description': 'Headphones used in multi-seller order demo.',
        'catid': 'cat_electronics',
        'userid': 'seller_demo_electronics',
        'image': 'https://picsum.photos/seed/demo-headphones/600/600',
    },
    {
        'proid': 'demo_pro_jacket',
        'name': 'Lightweight Jacket',
        'price': Decimal('299.00'),
        'stock': 35,
        'description': 'Fashion product for seller demo.',
        'catid': 'cat_clothing',
        'userid': 'seller_demo_fashion',
        'image': 'https://picsum.photos/seed/demo-jacket/600/600',
    },
    {
        'proid': 'demo_pro_sneakers',
        'name': 'Daily Sneakers',
        'price': Decimal('259.00'),
        'stock': 52,
        'description': 'Sneakers used in multi-seller order demo.',
        'catid': 'cat_clothing',
        'userid': 'seller_demo_fashion',
        'image': 'https://picsum.photos/seed/demo-sneakers/600/600',
    },
    {
        'proid': 'demo_pro_lamp',
        'name': 'Smart Desk Lamp',
        'price': Decimal('129.00'),
        'stock': 30,
        'description': 'Home product for seller demo.',
        'catid': 'cat_home_appliances',
        'userid': 'seller_demo_home',
        'image': 'https://picsum.photos/seed/demo-lamp/600/600',
    },
    {
        'proid': 'demo_pro_air_purifier',
        'name': 'Compact Air Purifier',
        'price': Decimal('499.00'),
        'stock': 18,
        'description': 'Home appliance used in multi-seller order demo.',
        'catid': 'cat_home_appliances',
        'userid': 'seller_demo_home',
        'image': 'https://picsum.photos/seed/demo-air-purifier/600/600',
    },
]

DEMO_ORDERS = [
    {
        'orderid': 'demo_order_electronics_pending',
        'sellerid': 'seller_demo_electronics',
        'status': 'pending',
        'items': [
            {'proid': 'demo_pro_keyboard', 'quantity': 1},
            {'proid': 'demo_pro_headphones', 'quantity': 1},
        ],
    },
    {
        'orderid': 'demo_order_fashion_pending',
        'sellerid': 'seller_demo_fashion',
        'status': 'pending',
        'items': [
            {'proid': 'demo_pro_jacket', 'quantity': 1},
            {'proid': 'demo_pro_sneakers', 'quantity': 2},
        ],
    },
    {
        'orderid': 'demo_order_home_pending',
        'sellerid': 'seller_demo_home',
        'status': 'pending',
        'items': [
            {'proid': 'demo_pro_lamp', 'quantity': 2},
            {'proid': 'demo_pro_air_purifier', 'quantity': 1},
        ],
    },
]


def _upsert(model, primary_key, values):
    instance = db.session.get(model, values[primary_key])
    if instance is None:
        instance = model(**values)
        db.session.add(instance)
        return instance

    for key, value in values.items():
        setattr(instance, key, value)
    return instance


def _seed_users():
    _upsert(User, 'userid', {
        'userid': DEMO_BUYER_ID,
        'username': DEMO_BUYER_USERNAME,
        'password': 'buyer123',
        'email': 'buyer.multi@example.com',
        'phone': '18800000999',
        'role': 'buyer',
        'shipping_address': 'Demo Road 100, Shanghai',
    })

    for seller in DEMO_SELLERS:
        _upsert(User, 'userid', {
            **seller,
            'role': 'seller',
            'shipping_address': None,
        })


def _seed_categories():
    for category in DEMO_CATEGORIES:
        _upsert(Category, 'catid', category)


def _seed_products():
    for product in DEMO_PRODUCTS:
        _upsert(Product, 'proid', product)


def _cleanup_legacy_demo_categories():
    for legacy_catid, target_catid in LEGACY_DEMO_CATEGORY_MAP.items():
        Product.query.filter_by(catid=legacy_catid).update(
            {'catid': target_catid},
            synchronize_session=False,
        )
        legacy_category = db.session.get(Category, legacy_catid)
        if legacy_category:
            db.session.delete(legacy_category)


def _seed_orders():
    order_ids = [order['orderid'] for order in DEMO_ORDERS]
    if order_ids:
        OrderItem.query.filter(OrderItem.orderid.in_(order_ids)).delete(synchronize_session=False)

    for order_data in DEMO_ORDERS:
        order = _upsert(Order, 'orderid', {
            'orderid': order_data['orderid'],
            'userid': DEMO_BUYER_ID,
            'sellerid': order_data['sellerid'],
            'status': order_data['status'],
            'totalprice': Decimal('0.00'),
        })

        totalprice = Decimal('0.00')
        for item_data in order_data['items']:
            product = db.session.get(Product, item_data['proid'])
            quantity = int(item_data['quantity'])
            totalprice += product.price * quantity
            db.session.add(OrderItem(
                orderid=order.orderid,
                proid=product.proid,
                productname=product.name,
                price=product.price,
                quantity=quantity,
            ))

        order.totalprice = totalprice


def seed_multiseller_demo_data():
    _seed_users()
    _seed_categories()
    _seed_products()
    _cleanup_legacy_demo_categories()
    _seed_orders()
    db.session.commit()

    return {
        'buyer_id': DEMO_BUYER_ID,
        'buyer_password': 'buyer123',
        'seller_count': len(DEMO_SELLERS),
        'product_count': len(DEMO_PRODUCTS),
        'order_count': len(DEMO_ORDERS),
        'seller_accounts': [
            {'userid': seller['userid'], 'username': seller['username']}
            for seller in DEMO_SELLERS
        ],
        'buyer_username': DEMO_BUYER_USERNAME,
        'seller_password': 'seller123',
    }
