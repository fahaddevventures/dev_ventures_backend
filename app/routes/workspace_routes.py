from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.schemas.workspace_schema import WorkspaceSchema
from app.schemas.user_schema import UserSchema
from app.enums import UserRoleEnum
from app.utils.role_required import role_required
from app.models.user import User
from app.utils.invite_code import generate_unique_invite_code

workspace_bp = Blueprint('workspace', __name__)

workspace_schema = WorkspaceSchema(session=db.session)
workspace_list_schema = WorkspaceSchema(many=True)
user_schema = UserSchema(session=db.session)
users_schema = UserSchema(many=True)

@workspace_bp.route('/', methods=['POST'])
@login_required
@role_required(UserRoleEnum.admin)
def create_workspace():
    data = request.json or {}

    # Validate request body
    errors = workspace_schema.validate(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    # Check if workspace name already exists
    existing = Workspace.query.filter_by(name=data.get("name")).first()
    if existing:
        return jsonify({"error": f"A workspace with the name '{data['name']}' already exists."}), 409

    try:
        workspace = workspace_schema.load(data)  # invite_code is generated inside model or pre-hook
        db.session.add(workspace)
        db.session.commit()

        return jsonify({
            "message": "Workspace created successfully.",
            "workspace": workspace_schema.dump(workspace)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@workspace_bp.route('/', methods=['GET'])
@login_required
def get_workspaces():
    workspaces = Workspace.query.order_by(Workspace.created_at.desc()).all()
    return jsonify(workspace_list_schema.dump(workspaces)), 200



@workspace_bp.route('/<int:workspace_id>', methods=['DELETE'])
@login_required
@role_required(UserRoleEnum.admin)
def delete_workspace(workspace_id):
    workspace = Workspace.query.get(workspace_id)

    if not workspace:
        return jsonify({"error": "Workspace not found"}), 404

    try:
        db.session.delete(workspace)
        db.session.commit()
        return jsonify({"message": "Workspace deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete workspace: {str(e)}"}), 500
    
@workspace_bp.route('/join', methods=['POST'])
@login_required
def join_workspace():
    data = request.json or {}

    invite_code = data.get("invite_code")
    if not invite_code:
        return jsonify({"error": "Invite code is required."}), 400

    # Find the workspace
    workspace = Workspace.query.filter_by(invite_code=invite_code).first()
    if not workspace:
        return jsonify({"error": "Invalid invite code."}), 404

    # Check if user is already a member
    existing_member = WorkspaceMember.query.filter_by(
        user_id=current_user.id,
        workspace_id=workspace.id
    ).first()

    if existing_member:
        return jsonify({"message": "You are already a member of this workspace."}), 200

    # Add user to workspace
    try:
        new_member = WorkspaceMember(
            user_id=current_user.id,
            workspace_id=workspace.id
        )
        db.session.add(new_member)
        db.session.commit()

        return jsonify({
            "message": "Successfully joined the workspace.",
            "workspace": {
                "id": workspace.id,
                "name": workspace.name
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to join workspace: {str(e)}"}), 500
    
@workspace_bp.route('/my-workspaces', methods=['GET'])
@login_required
def get_my_workspaces():
    memberships = WorkspaceMember.query.filter_by(user_id=current_user.id).all()
    
    workspaces = [membership.workspace for membership in memberships]

    
    schema = WorkspaceSchema(many=True)
    return jsonify(schema.dump(workspaces)), 200

@workspace_bp.route('/<int:workspace_id>/members/<int:user_id>', methods=['DELETE'])
@login_required
@role_required(UserRoleEnum.admin)
def remove_workspace_member(workspace_id, user_id):
    # Check if workspace exists
    workspace = Workspace.query.get(workspace_id)
    if not workspace:
        return jsonify({"error": "Workspace not found."}), 404

    # Check if user exists
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    # Find the membership
    membership = WorkspaceMember.query.filter_by(user_id=user_id, workspace_id=workspace_id).first()
    if not membership:
        return jsonify({"error": "User is not a member of this workspace."}), 404

    try:
        db.session.delete(membership)
        db.session.commit()
        return jsonify({"message": f"User {user.email} removed from workspace {workspace.name}."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to remove member: {str(e)}"}), 500
    
@workspace_bp.route('/<int:workspace_id>/leave', methods=['DELETE'])
@login_required
def leave_workspace(workspace_id):
    # Check if workspace exists
    workspace = Workspace.query.get(workspace_id)
    if not workspace:
        return jsonify({"error": "Workspace not found."}), 404

    # Check if user is part of the workspace
    membership = WorkspaceMember.query.filter_by(
        user_id=current_user.id,
        workspace_id=workspace_id
    ).first()

    if not membership:
        return jsonify({"error": "You are not a member of this workspace."}), 400

    try:
        db.session.delete(membership)
        db.session.commit()
        return jsonify({
            "message": f"You have successfully left the workspace '{workspace.name}'."
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to leave workspace: {str(e)}"}), 500
    
@workspace_bp.route('/<int:workspace_id>', methods=['GET'])
@login_required
def get_workspace_by_id(workspace_id):
    workspace = Workspace.query.get(workspace_id)

    if not workspace:
        return jsonify({"error": "Workspace not found."}), 404

    return jsonify({
        "workspace": workspace_schema.dump(workspace)
    }), 200


@workspace_bp.route('/<int:workspace_id>/members', methods=['GET'])
@login_required
def get_workspace_members(workspace_id):
    workspace = Workspace.query.get(workspace_id)
    if not workspace:
        return jsonify({"error": "Workspace not found."}), 404

    members = WorkspaceMember.query.filter_by(workspace_id=workspace_id).all()
    users = [member.user for member in members]

    return jsonify({
        "workspace_id": workspace.id,
        "workspace_name": workspace.name,
        "members": users_schema.dump(users)
    }), 200



@workspace_bp.route('/<int:workspace_id>', methods=['PATCH'])
@login_required
@role_required(UserRoleEnum.admin)
def update_workspace(workspace_id):
    data = request.json or {}

    if 'name' not in data or not data['name'].strip():
        return jsonify({"error": "Workspace name is required"}), 400

    workspace = Workspace.query.get(workspace_id)
    if not workspace:
        return jsonify({"error": "Workspace not found"}), 404

    new_name = data['name'].strip()

    # Check if the new name already exists (excluding current workspace)
    existing = Workspace.query.filter(
        Workspace.name == new_name,
        Workspace.id != workspace_id
    ).first()
    if existing:
        return jsonify({"error": "Workspace name already in use"}), 409

    workspace.name = new_name
    workspace.invite_code = generate_unique_invite_code(new_name)

    db.session.commit()

    return jsonify({
        "message": "Workspace updated successfully",
        "workspace": workspace_schema.dump(workspace)
    }), 200