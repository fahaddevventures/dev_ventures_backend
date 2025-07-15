from flask import Blueprint, request, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models.user import User
from app.enums import UserRoleEnum
from app.utils.role_required import role_required

auth_bp = Blueprint('auth', __name__)

from app.schemas.user_schema import UserSchema
from marshmallow import ValidationError

user_schema = UserSchema(session=db.session)

@auth_bp.route('/register', methods=['POST'])
@login_required
@role_required(UserRoleEnum.admin, UserRoleEnum.team_lead)
def register():
    data = request.json or {}

    # Check if user exists first
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({"error": "User already exists"}), 409

    try:
        # Ensure password_hash gets hashed before creation
        data['password'] = generate_password_hash(data['password'])  # You keep using "password" in input
        data['role'] = data.get('role', 'employee')

        validated_data = user_schema.load(data)

        # Convert string to Enum
        validated_data.role = UserRoleEnum[validated_data.role] if isinstance(validated_data.role, str) else validated_data.role

        db.session.add(validated_data)
        db.session.commit()

        return jsonify({
            "message": "User registered successfully",
            "user": user_schema.dump(validated_data)
        }), 201

    except ValidationError as e:
        return jsonify({"errors": e.messages}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal error: {str(e)}"}), 500




@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "error": "Validation error",
            "message": "Both email and password are required."
        }), 400

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({
            "error": "Authentication failed",
            "message": "Invalid email or password."
        }), 401

    if not user.is_active:
        return jsonify({
            "error": "Account deactivated",
            "message": "Your account is deactivated. Please contact admin."
        }), 403

    login_user(user)

    return jsonify({
        "message": "Login successful",
        "user": user_schema.dump(user)
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"}), 200


@auth_bp.route('/current-user', methods=['GET'])
@login_required
def get_profile():
    return jsonify({
        "id": current_user.id,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email": current_user.email,
        "profile_image_url": current_user.profile_image_url,
        "role": current_user.role.value
    })