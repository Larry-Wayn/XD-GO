from flask import Blueprint, jsonify, request

from backend.services.seller_insight_ai import generate_seller_insight
from backend.services.seller_insight_metrics import (
    get_seller_insight_metrics,
    parse_insight_days,
)
from backend.services.seller_insight_retriever import retrieve_seller_insight_knowledge
from backend.views.auth import token_required

main = Blueprint('seller_insights', __name__)


@main.route('/insights', methods=['GET'])
@token_required
def get_seller_insights(current_user):
    if current_user.role != 'seller':
        return jsonify({"code": 403, "message": "无权访问"}), 403
    try:
        days = parse_insight_days(request.args.get('days', 30))
        metrics = get_seller_insight_metrics(current_user.userid, days=days)
        knowledge_snippets = retrieve_seller_insight_knowledge(metrics)
        insight = generate_seller_insight(metrics, knowledge_snippets=knowledge_snippets)
        return jsonify({
            "code": 200,
            "message": "获取卖家运营洞察成功",
            "data": insight
        }), 200
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"服务器错误: {str(e)}"
        }), 500
