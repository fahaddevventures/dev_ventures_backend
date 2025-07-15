from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.workspace import Workspace
from app.schemas.workspace_schema import WorkspaceSchema
from app.enums import UserRoleEnum
from app.utils.role_required import role_required

workspace_bp = Blueprint('workspace', __name__)
workspace_schema = WorkspaceSchema()
workspace_list_schema = WorkspaceSchema(many=True)

@workspace_bp.route('/workspaces', methods=['POST'])
@login_required
@role_required(UserRoleEnum.admin)
def create_workspace():
    data = request.get_json() or {}

    errors = workspace_schema.validate(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    if Workspace.query.filter_by(invite_code=data["invite_code"]).first():
        return jsonify({"error": "Invite code already exists."}), 409

    workspace = workspace_schema.load(data)
    db.session.add(workspace)
    db.session.commit()

    return jsonify({
        "message": "Workspace created successfully.",
        "workspace": workspace_schema.dump(workspace)
    }), 201

@workspace_bp.route('/workspaces', methods=['GET'])
@login_required
def get_workspaces():
    workspaces = Workspace.query.order_by(Workspace.created_at.desc()).all()
    return jsonify(workspace_list_schema.dump(workspaces)), 200
