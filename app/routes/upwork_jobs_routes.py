from flask import Blueprint, request, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.upwork_job import UpworkJob
from app.schemas.upwork_jobs_schema import UpworkJobSchema
from app.enums import UserRoleEnum
from app.utils.role_required import role_required
from app.utils.gemini import assess_job_feasibility


upwork_job_bp = Blueprint('upwork_job', __name__)

upwork_jobs_schema = UpworkJobSchema(session=db.session)
upwork_jobs_list_schema = UpworkJobSchema(many=True)


@upwork_job_bp.route('/', methods=['POST'])
@login_required
@role_required(UserRoleEnum.admin, UserRoleEnum.team_lead, UserRoleEnum.salesman)
def create_upwork_job():
    data = request.json or {}

    # Step 1: Validate basic schema (excluding feasibility_status)
    errors = upwork_jobs_schema.validate(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    # Step 2: Check if job ID already exists
    if UpworkJob.query.filter_by(job_id=data.get("job_id")).first():
        return jsonify({"error": f"Job ID '{data['job_id']}' already exists."}), 409

    try:
        # Step 3: Call Gemini to get feasibility status
        feasibility = assess_job_feasibility(data)
        data['feasibility_status'] = feasibility

        # Step 4: Deserialize and load full object including AI result
        upwork_job = upwork_jobs_schema.load(data)

        # Step 5: Save to DB
        db.session.add(upwork_job)
        db.session.commit()

        return jsonify({
            "message": "Upwork job created successfully.",
            "job": upwork_jobs_schema.dump(upwork_job)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal error: {str(e)}"}), 500
