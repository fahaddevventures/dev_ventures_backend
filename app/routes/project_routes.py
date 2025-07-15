from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.project import Project
from app.models.workspace_member import WorkspaceMember
from app.schemas.project_schema import ProjectSchema
from app.schemas.user_schema import UserSchema
from app.enums import UserRoleEnum
from app.utils.role_required import role_required
from app.models.user import User
from app.utils.invite_code import generate_unique_invite_code
from app.models.project_member import ProjectMember
from app.schemas.project_member_schema import ProjectMemberSchema

project_bp = Blueprint('project', __name__)

project_schema = ProjectSchema(session=db.session)
project_list_schema = ProjectSchema(many=True)
project_members_schema = ProjectMemberSchema(session=db.session)
project_members_list_schema = ProjectMemberSchema(many=True)
user_schema = UserSchema(session=db.session)
users_schema = UserSchema(many=True)


@project_bp.route('/', methods=['POST'])
@login_required
@role_required(UserRoleEnum.admin, UserRoleEnum.team_lead)
def create_project():
    data = request.json or {}

    # Step 1: Validate request body
    errors = project_schema.validate(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    # Step 2: Check for existing project with same name in same workspace (optional business rule)
    existing = Project.query.filter_by(name=data.get("name"), workspace_id=data.get("workspace_id")).first()
    if existing:
        return jsonify({"error": f"A project named '{data['name']}' already exists in this workspace."}), 409

    try:
        # Step 3: Deserialize and create project
        project = project_schema.load(data)

        # Step 4: Save to DB
        db.session.add(project)
        db.session.commit()

        return jsonify({
            "message": "Project created successfully.",
            "project": project_schema.dump(project)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@project_bp.route('/<int:project_id>', methods=['GET'])
@login_required
@role_required(UserRoleEnum.admin, UserRoleEnum.team_lead)
def get_project_by_id(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": f"Project with ID {project_id} not found."}), 404

        return jsonify({
            "project": project_schema.dump(project)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    


@project_bp.route('/', methods=['GET'])
@login_required
@role_required(UserRoleEnum.admin, UserRoleEnum.team_lead)
def get_all_projects():
    try:
        projects = Project.query.all()
        return jsonify({
            "projects": project_list_schema.dump(projects)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500




@project_bp.route('/<int:project_id>', methods=['DELETE'])
@login_required
@role_required(UserRoleEnum.admin)
def delete_project(project_id):
    project = Project.query.get(project_id)

    if not project:
        return jsonify({"error": f"Project with ID {project_id} not found."}), 404

    try:
        db.session.delete(project)
        db.session.commit()

        return jsonify({
            "message": f"Project '{project.name}' (ID: {project_id}) deleted successfully."
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500




@project_bp.route('/team-lead', methods=['GET'])
@login_required
def get_projects_as_team_lead():
    try:
        # Filter projects where current user is the team lead
        projects = Project.query.filter_by(team_lead_id=current_user.id).all()

        return jsonify({
            "projects": project_list_schema.dump(projects)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500





@project_bp.route('/add-member', methods=['POST'])
@login_required
@role_required(UserRoleEnum.admin, UserRoleEnum.team_lead)
def add_user_to_project():
    data = request.json or {}

    # Step 1: Validate input schema
    errors = project_members_schema.validate(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    user_id = data.get("user_id")
    project_id = data.get("project_id")

    # Step 2: Check if user exists
    if not User.query.get(user_id):
        return jsonify({"error": f"User with id {user_id} does not exist."}), 404

    # Step 3: Check if project exists
    if not Project.query.get(project_id):
        return jsonify({"error": f"Project with id {project_id} does not exist."}), 404

    # Step 4: Check if user is already part of the project
    existing_member = ProjectMember.query.filter_by(user_id=user_id, project_id=project_id).first()
    if existing_member:
        return jsonify({"error": "User is already a member of this project."}), 409

    try:
        # Step 5: Create and store project member
        project_member = project_members_schema.load(data)
        db.session.add(project_member)
        db.session.commit()

        return jsonify({
            "message": "User added to project successfully.",
            "member": project_members_schema.dump(project_member)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500







@project_bp.route('/my-projects', methods=['GET'])
@login_required
def get_my_projects():
    try:
        # Get all projects the current user is a member of
        projects = Project.query.join(Project.members).filter_by(user_id=current_user.id).all()

        return jsonify({
            "projects": project_list_schema.dump(projects)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    

@project_bp.route('/<int:project_id>/members/<int:user_id>', methods=['DELETE'])
@login_required
def remove_project_member(project_id, user_id):
    try:
        membership = ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).first()

        if not membership:
            return jsonify({"error": "Member not found in this project."}), 404

        db.session.delete(membership)
        db.session.commit()

        return jsonify({"message": f"User {user_id} removed from project {project_id}."}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500



@project_bp.route('/<int:project_id>/members', methods=['GET'])
@login_required
def list_project_members(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": f"Project with ID {project_id} not found."}), 404

        members = ProjectMember.query.filter_by(project_id=project_id).all()
        return jsonify({
            "project_id": project_id,
            "members": project_members_list_schema.dump(members)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    

@project_bp.route('/workspace/<int:workspace_id>', methods=['GET'])
@login_required
def get_projects_by_workspace(workspace_id):
    try:
        projects = Project.query.filter_by(workspace_id=workspace_id).all()

        return jsonify({
            "workspace_id": workspace_id,
            "total": len(projects),
            "projects": project_list_schema.dump(projects)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    
@project_bp.route('/update/<int:project_id>', methods=['PUT'])
@login_required
@role_required(UserRoleEnum.admin, UserRoleEnum.team_lead)
def update_project(project_id):
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"error": f"Project with ID {project_id} not found."}), 404

    data = request.json or {}

    # Validate input
    errors = project_schema.validate(data, partial=True)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    try:
        # Update fields
        for key, value in data.items():
            setattr(project, key, value)

        db.session.commit()

        return jsonify({
            "message": "Project updated successfully.",
            "project": project_schema.dump(project)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500