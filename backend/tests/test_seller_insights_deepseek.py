import json
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from flask import Flask

from backend import db
from backend.models import Category, Order, OrderItem, Product, User
from backend.services.seller_insight_ai import generate_seller_insight
from backend.services.seller_insight_metrics import get_seller_insight_metrics


@pytest.fixture
def app():
    test_app = Flask(__name__)
    test_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(test_app)

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


def _seed_store(now=None):
    now = now or datetime.utcnow()
    db.session.add_all([
        User(userid='seller_1', username='seller', password='pw', email='seller@example.com', role='seller'),
        User(userid='buyer_1', username='buyer', password='pw', email='buyer@example.com', role='buyer'),
        Category(catid='cat_1', name='Electronics'),
        Product(proid='pro_hot', name='Hot Keyboard', price=Decimal('100.00'), stock=3, description='hot', catid='cat_1', userid='seller_1'),
    ])
    db.session.add(Order(
        orderid='order_shipped', userid='buyer_1', sellerid='seller_1',
        status='shipped', totalprice=Decimal('200.00'), createtime=now - timedelta(days=2)
    ))
    db.session.add(OrderItem(
        orderid='order_shipped', proid='pro_hot', productname='Hot Keyboard',
        price=Decimal('100.00'), quantity=2
    ))
    db.session.commit()


def _metrics(app):
    with app.app_context():
        _seed_store()
        return get_seller_insight_metrics('seller_1', days=30)


def test_missing_deepseek_key_uses_fallback(app, monkeypatch):
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)

    payload = generate_seller_insight(_metrics(app))

    assert payload['meta']['source'] == 'fallback'


def test_deepseek_success_uses_chat_completions(app, monkeypatch):
    class Message:
        content = '{"briefing": "DeepSeek generated briefing", "cards": [{"title": "处理待发货", "priority": "high", "recommendation": "先发货", "reason": "有待发货订单", "evidence": ["待发货订单: 1"], "metric": "pending_orders"}]}'

    class Choice:
        message = Message()

    class Response:
        choices = [Choice()]

    class Completions:
        def __init__(self):
            self.kwargs = None

        def create(self, **kwargs):
            self.kwargs = kwargs
            return Response()

    class Chat:
        def __init__(self):
            self.completions = Completions()

    class Client:
        def __init__(self):
            self.chat = Chat()

    client = Client()
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-key')
    monkeypatch.setenv('DEEPSEEK_MODEL', 'deepseek-v4-flash')

    knowledge_snippets = [{
        "id": "inventory_restocking",
        "title": "库存补货策略",
        "topic": "low_stock",
        "content": "低库存商品需要确认库存和补货。",
        "score": 100,
    }]

    payload = generate_seller_insight(
        _metrics(app),
        client=client,
        knowledge_snippets=knowledge_snippets,
    )

    assert payload['meta']['source'] == 'deepseek'
    assert payload['meta']['ragEnabled'] is True
    assert payload['meta']['knowledgeSourceCount'] == 1
    assert payload['meta']['knowledgeSources'][0]['title'] == '库存补货策略'
    assert payload['briefing'] == 'DeepSeek generated briefing'
    assert client.chat.completions.kwargs['model'] == 'deepseek-v4-flash'
    assert 'response_format' not in client.chat.completions.kwargs

    user_message = client.chat.completions.kwargs['messages'][1]
    prompt_payload = json.loads(user_message['content'])
    assert prompt_payload['retrievedKnowledge'][0]['title'] == '库存补货策略'
    assert prompt_payload['retrievedKnowledge'][0]['content'] == '低库存商品需要确认库存和补货。'


def test_deepseek_exception_returns_fallback_without_rag_enabled(app, monkeypatch):
    class BrokenCompletions:
        def create(self, **kwargs):
            raise RuntimeError('network down')

    class BrokenChat:
        completions = BrokenCompletions()

    class BrokenClient:
        chat = BrokenChat()

    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-key')

    payload = generate_seller_insight(
        _metrics(app),
        client=BrokenClient(),
        knowledge_snippets=[{
            "id": "inventory_restocking",
            "title": "库存补货策略",
            "topic": "low_stock",
            "content": "低库存商品需要确认库存和补货。",
        }],
    )

    assert payload['meta']['source'] == 'fallback'
    assert payload['meta']['ragEnabled'] is False
    assert payload['meta']['knowledgeSources'] == []


def test_invalid_deepseek_json_uses_fallback(app, monkeypatch):
    class Message:
        content = '{"briefing": "ok", "cards": []}'

    class Choice:
        message = Message()

    class Response:
        choices = [Choice()]

    class Completions:
        def create(self, **kwargs):
            return Response()

    class Chat:
        completions = Completions()

    class Client:
        chat = Chat()

    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-key')

    payload = generate_seller_insight(_metrics(app), client=Client())

    assert payload['meta']['source'] == 'fallback'
