from flask import Blueprint, jsonify
from app.models.user import User



user_bp = Blueprint('user', __name__)

@user_bp.route('/', methods=['GET'])
def get_all_users():
    # users = User.query.all()
    return jsonify([{'id': 'user.id', 'email': 'user.email', 'role': 'user.role'}])

