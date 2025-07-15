from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.project import Project
from app.models.task import Task
from app.schemas.task_schema import TaskSchema
from app.schemas.user_schema import UserSchema
from app.enums import UserRoleEnum
from app.utils.role_required import role_required
from app.models.user import User
from app.utils.invite_code import generate_unique_invite_code

task_bp = Blueprint('task', __name__)

task_schema = TaskSchema(session=db.session)
task_list_schema = TaskSchema(many=True)
task_schema_partial = TaskSchema(partial=True)
user_schema = UserSchema(session=db.session)
users_schema = UserSchema(many=True)



@task_bp.route('/', methods=['POST'])
@login_required
@role_required(UserRoleEnum.admin, UserRoleEnum.team_lead)
def create_task():
    data = request.json or {}

    # ✅ Validate incoming data (excluding task_code and created_by)
    errors = task_schema.validate(data, partial=("task_code", "created_by"))
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    project_id = data.get('project_id')
    assigned_to = data.get('assigned_to')

    # ✅ Check if project exists
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"error": f"Project with id {project_id} does not exist."}), 404

    # ✅ Check if assigned user exists
    user = User.query.get(assigned_to)
    if not user:
        return jsonify({"error": f"User with id {assigned_to} does not exist."}), 404

    data["task_code"] = generate_unique_invite_code("TSK")
    # Check for task_code duplication (edge case: extremely rare with UUID, but still good to check)
    if Task.query.filter_by(task_code=data["task_code"]).first():
        return jsonify({"error": f"Task with code '{data["task_code"]}' already exists."}), 409

    # ✅ Assign creator
    data["created_by"] = current_user.id

    try:
        task = task_schema.load(data)
        db.session.add(task)
        db.session.commit()

        return jsonify({
            "message": "Task created successfully.",
            "task": task_schema.dump(task)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500



@task_bp.route('/<int:task_id>', methods=['DELETE'])
@login_required
@role_required(UserRoleEnum.admin, UserRoleEnum.team_lead)
def delete_task(task_id):
    task = Task.query.get(task_id)

    if not task:
        return jsonify({"error": f"Task with ID {task_id} not found."}), 404

    try:
        db.session.delete(task)
        db.session.commit()

        return jsonify({
            "message": f"Task '{task.task_code}' deleted successfully."
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500



@task_bp.route('/', methods=['GET'])
@login_required
@role_required(UserRoleEnum.admin, UserRoleEnum.team_lead)
def get_all_tasks():
    try:
        tasks = Task.query.order_by(Task.created_at.desc()).all()
        return jsonify({
            "tasks": task_list_schema.dump(tasks)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500





@task_bp.route('/<int:task_id>', methods=['GET'])
@login_required
@role_required(UserRoleEnum.admin, UserRoleEnum.team_lead)
def get_task_by_id(task_id):
    task = Task.query.get(task_id)

    if not task:
        return jsonify({"error": f"Task with ID {task_id} not found."}), 404

    return jsonify({
        "task": task_schema.dump(task)
    }), 200



@task_bp.route('/<int:task_id>', methods=['PUT'])
@login_required
@role_required(UserRoleEnum.admin, UserRoleEnum.team_lead)
def update_task(task_id):
    data = request.json or {}

    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": f"Task with ID {task_id} not found."}), 404

    # Optional: Check project existence if being changed
    if "project_id" in data:
        project = Project.query.get(data["project_id"])
        if not project:
            return jsonify({"error": f"Project with ID {data['project_id']} does not exist."}), 400

    # Optional: Check assigned user existence if being changed
    if "assigned_to" in data:
        user = User.query.get(data["assigned_to"])
        if not user:
            return jsonify({"error": f"Assigned user with ID {data['assigned_to']} does not exist."}), 400


    # Validate input with session
    errors = task_schema_partial.validate(data, session=db.session)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    try:
        task = task_schema_partial.load(data, instance=task, session=db.session)
        db.session.commit()

        return jsonify({
            "message": "Task updated successfully.",
            "task": task_schema.dump(task)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500