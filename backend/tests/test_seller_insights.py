from datetime import datetime, timedelta
from decimal import Decimal

import jwt
import pytest
from flask import Flask

from backend import db
from backend.models import Category, Order, OrderItem, Product, User
from backend.services.seller_insight_ai import generate_seller_insight
from backend.services.seller_insight_fallback import build_fallback_insight
from backend.services.seller_insight_metrics import get_seller_insight_metrics
from backend.views.seller_insights import main as seller_insights_blueprint


@pytest.fixture
def app():
    test_app = Flask(__name__)
    test_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(test_app)
    test_app.register_blueprint(seller_insights_blueprint, url_prefix='/api/sell_order')

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


def _seed_store(now=None):
    now = now or datetime.utcnow()
    seller = User(
        userid='seller_1', username='seller', password='pw',
        email='seller@example.com', role='seller'
    )
    buyer = User(
        userid='buyer_1', username='buyer', password='pw',
        email='buyer@example.com', role='buyer'
    )
    category = Category(catid='cat_1', name='Electronics')
    products = [
        Product(
            proid='pro_hot', name='Hot Keyboard', price=Decimal('100.00'),
            stock=3, description='hot', catid='cat_1', userid='seller_1'
        ),
        Product(
            proid='pro_slow', name='Slow Mouse', price=Decimal('50.00'),
            stock=80, description='slow', catid='cat_1', userid='seller_1'
        ),
    ]
    db.session.add_all([seller, buyer, category] + products)

    shipped = Order(
        orderid='order_shipped', userid='buyer_1', sellerid='seller_1',
        status='shipped', totalprice=Decimal('200.00'), createtime=now - timedelta(days=2)
    )
    delivered = Order(
        orderid='order_delivered', userid='buyer_1', sellerid='seller_1',
        status='delivered', totalprice=Decimal('100.00'), createtime=now - timedelta(days=3)
    )
    pending = Order(
        orderid='order_pending', userid='buyer_1', sellerid='seller_1',
        status='pending', totalprice=Decimal('100.00'), createtime=now - timedelta(days=1)
    )
    db.session.add_all([shipped, delivered, pending])
    db.session.add_all([
        OrderItem(orderid='order_shipped', proid='pro_hot', productname='Hot Keyboard', price=Decimal('100.00'), quantity=2),
        OrderItem(orderid='order_delivered', proid='pro_hot', productname='Hot Keyboard', price=Decimal('100.00'), quantity=1),
        OrderItem(orderid='order_pending', proid='pro_hot', productname='Hot Keyboard', price=Decimal('100.00'), quantity=1),
    ])
    db.session.commit()
    return seller


def test_metrics_aggregate_recent_seller_orders(app):
    now = datetime(2026, 6, 22, 12, 0, 0)
    with app.app_context():
        _seed_store(now=now)
        metrics = get_seller_insight_metrics('seller_1', days=30, now=now)

    assert metrics['windowDays'] == 30
    assert metrics['orderCount'] == 3
    assert metrics['revenue'] == 300.0
    assert metrics['pendingOrders'] == 1
    assert metrics['topProducts'][0]['productName'] == 'Hot Keyboard'
    assert metrics['topProducts'][0]['quantitySold'] == 3
    assert metrics['lowStockProducts'][0]['productName'] == 'Hot Keyboard'
    assert metrics['slowMovingProducts'][0]['productName'] == 'Slow Mouse'


def test_empty_store_fallback_returns_safe_payload(app):
    with app.app_context():
        db.session.add(User(
            userid='seller_1', username='seller', password='pw',
            email='seller@example.com', role='seller'
        ))
        db.session.commit()
        metrics = get_seller_insight_metrics('seller_1', days=30)
        payload = build_fallback_insight(metrics)

    assert payload['meta']['source'] == 'fallback'
    assert payload['meta']['ragEnabled'] is False
    assert payload['meta']['knowledgeSourceCount'] == 0
    assert payload['meta']['knowledgeSources'] == []
    assert payload['metrics']['orderCount'] == 0
    assert payload['briefing']
    assert payload['cards'][0]['priority'] == 'low'


def test_missing_openai_key_uses_fallback(app, monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    with app.app_context():
        _seed_store()
        metrics = get_seller_insight_metrics('seller_1', days=30)
        payload = generate_seller_insight(metrics)

    assert payload['meta']['source'] == 'fallback'
    assert payload['cards']


def test_openai_exception_uses_fallback(app, monkeypatch):
    class BrokenResponses:
        def create(self, **kwargs):
            raise RuntimeError('network down')

    class BrokenClient:
        responses = BrokenResponses()

    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    with app.app_context():
        _seed_store()
        metrics = get_seller_insight_metrics('seller_1', days=30)
        payload = generate_seller_insight(metrics, client=BrokenClient())

    assert payload['meta']['source'] == 'fallback'


def test_invalid_model_json_uses_fallback(app, monkeypatch):
    class Response:
        output_text = '{"briefing": "ok", "cards": []}'

    class Responses:
        def create(self, **kwargs):
            return Response()

    class Client:
        responses = Responses()

    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    with app.app_context():
        _seed_store()
        metrics = get_seller_insight_metrics('seller_1', days=30)
        payload = generate_seller_insight(metrics, client=Client())

    assert payload['meta']['source'] == 'fallback'


def test_buyer_cannot_request_seller_insights(app, client):
    with app.app_context():
        db.session.add(User(
            userid='buyer_1', username='buyer', password='pw',
            email='buyer@example.com', role='buyer'
        ))
        db.session.commit()

    response = client.get(
        '/api/sell_order/insights?days=30',
        headers={'Authorization': f'Bearer {_token("buyer_1")}'},
    )

    assert response.status_code == 403
    assert response.get_json()['code'] == 403


def test_seller_insights_endpoint_returns_fallback_payload(app, client, monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    with app.app_context():
        _seed_store()

    response = client.get(
        '/api/sell_order/insights?days=99',
        headers={'Authorization': f'Bearer {_token("seller_1")}'},
    )

    body = response.get_json()
    assert response.status_code == 200
    assert body['code'] == 200
    assert body['data']['meta']['source'] == 'fallback'
    assert body['data']['meta']['windowDays'] == 30
    assert body['data']['meta']['ragEnabled'] is False
    assert body['data']['meta']['knowledgeSourceCount'] == 0
    assert body['data']['meta']['knowledgeSources'] == []
    assert body['data']['briefing']
    assert body['data']['cards']


def test_seller_insights_endpoint_passes_knowledge_to_ai(app, client, monkeypatch):
    captured = {}
    knowledge_snippets = [{
        "id": "inventory_restocking",
        "title": "库存补货策略",
        "topic": "low_stock",
        "content": "低库存商品需要确认库存和补货。",
        "sourcePath": "inventory_restocking.md",
        "score": 100,
    }]

    def fake_generate_seller_insight(metrics, knowledge_snippets=None):
        captured["metrics"] = metrics
        captured["knowledge_snippets"] = knowledge_snippets
        from backend.services.seller_insight_schema import build_insight_payload
        return build_insight_payload(
            "知识增强简报",
            [{
                "title": "补货建议",
                "priority": "high",
                "recommendation": "优先补货热销低库存商品。",
                "reason": "低库存商品需要确认库存和补货。",
                "evidence": ["低库存商品 1 个"],
                "metric": "low_stock",
            }],
            metrics,
            "deepseek",
            knowledge_sources=knowledge_snippets,
            rag_enabled=True,
        )

    monkeypatch.setattr(
        "backend.views.seller_insights.generate_seller_insight",
        fake_generate_seller_insight,
    )
    monkeypatch.setattr(
        "backend.views.seller_insights.retrieve_seller_insight_knowledge",
        lambda metrics: knowledge_snippets,
    )

    with app.app_context():
        _seed_store()

    response = client.get(
        '/api/sell_order/insights?days=30',
        headers={'Authorization': f'Bearer {_token("seller_1")}'},
    )

    body = response.get_json()
    assert response.status_code == 200
    assert body['data']['meta']['ragEnabled'] is True
    assert body['data']['meta']['knowledgeSourceCount'] >= 1
    assert captured["knowledge_snippets"]
    assert any(
        snippet["id"] == "inventory_restocking"
        for snippet in captured["knowledge_snippets"]
    )


def test_build_fallback_ignores_knowledge_sources_for_stable_degraded_mode(app):
    with app.app_context():
        _seed_store()
        metrics = get_seller_insight_metrics('seller_1', days=30)
        payload = build_fallback_insight(metrics, knowledge_sources=[{
            "id": "inventory_restocking",
            "title": "库存补货策略",
            "topic": "low_stock",
            "content": "补货内容",
            "score": 100,
        }])

    assert payload['meta']['source'] == 'fallback'
    assert payload['meta']['ragEnabled'] is False
    assert payload['meta']['knowledgeSourceCount'] == 0
    assert payload['meta']['knowledgeSources'] == []
