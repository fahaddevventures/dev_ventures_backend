from flask import Blueprint, request, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.upwork_job import UpworkJob
from app.schemas.upwork_jobs_schema import UpworkJobSchema
from app.enums import UserRoleEnum
from app.utils.role_required import role_required
from app.utils.gemini import assess_job_feasibility
from app.utils.gemini import generate_dummy_upwork_jobs

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


@upwork_job_bp.route('/all', methods=['GET'])
@login_required
def get_all_upwork_jobs():
    try:
        jobs = UpworkJob.query.order_by(UpworkJob.created_at.desc()).all()
        return jsonify({
            "jobs": upwork_jobs_list_schema.dump(jobs),
            "count": len(jobs)
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch jobs: {str(e)}"}), 500
    

@upwork_job_bp.route('/<int:job_id>', methods=['GET'])
@login_required
def get_upwork_job(job_id):
    job = UpworkJob.query.get(job_id)
    if not job:
        return jsonify({"error": f"No job found with ID {job_id}"}), 404

    return jsonify({
        "job": upwork_jobs_schema.dump(job)
    }), 200

@upwork_job_bp.route('/generate-dummy-jobs', methods=['POST'])
def generate_dummy_jobs():
    try:
        # Call Gemini utility to generate 10 dummy jobs
        jobs = generate_dummy_upwork_jobs()

        return jsonify({
            "message": "10 dummy jobs generated successfully.",
            "jobs": jobs
        }), 200

    except Exception as e:
        return jsonify({
            "error": f"Failed to generate dummy jobs: {str(e)}"
        }), 500
    

@upwork_job_bp.route('/bulk-create', methods=['POST'])
@login_required
@role_required(UserRoleEnum.admin, UserRoleEnum.team_lead, UserRoleEnum.salesman)
def bulk_create_upwork_jobs():
    jobs_data = generate_dummy_upwork_jobs()

    if not isinstance(jobs_data, list):
        return jsonify({"error": "Expected a list of jobs"}), 400

    created_jobs = []
    skipped_jobs = []
    errors = []

    for idx, job_data in enumerate(jobs_data):
        try:
            # Step 1: Basic validation
            validation_errors = upwork_jobs_schema.validate(job_data)
            if validation_errors:
                errors.append({
                    "job_index": idx,
                    "job_id": job_data.get("job_id"),
                    "error": validation_errors
                })
                continue

            # Step 2: Check for duplicates
            if UpworkJob.query.filter_by(job_id=job_data.get("job_id")).first():
                skipped_jobs.append(job_data.get("job_id"))
                continue

            # Step 3: AI feasibility assessment
            job_data['feasibility_status'] = assess_job_feasibility(job_data)

            # Step 4: Deserialize and add to session
            upwork_job = upwork_jobs_schema.load(job_data)
            db.session.add(upwork_job)
            created_jobs.append(upwork_job)

        except Exception as e:
            errors.append({
                "job_index": idx,
                "job_id": job_data.get("job_id"),
                "error": str(e)
            })

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to commit jobs: {str(e)}"}), 500

    return jsonify({
        "message": "Bulk job insert complete.",
        "created": [upwork_jobs_schema.dump(job) for job in created_jobs],
        "skipped_existing_job_ids": skipped_jobs,
        "errors": errors
    }), 207  # 207 Multi-Status: Some succeeded, some failed
