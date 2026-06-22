import jwt
import pytest
from flask import Flask

from backend import db
from backend.models import User
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


def test_admin_cannot_request_seller_insights(app, client):
    with app.app_context():
        db.session.add(User(
            userid='admin_1', username='admin', password='pw',
            email='admin@example.com', role='admin'
        ))
        db.session.commit()

    response = client.get(
        '/api/sell_order/insights?days=30',
        headers={'Authorization': f'Bearer {_token("admin_1")}'},
    )

    assert response.status_code == 403
    assert response.get_json()['code'] == 403
