from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.proposal import Proposal
from app.models.upwork_job import UpworkJob
from app.schemas.proposal_schema import ProposalSchema
from app.utils.gemini import assess_proposal_from_job, extract_json_from_text
from app.enums import ProposalStatusEnum

proposal_bp = Blueprint('proposal', __name__)

proposal_schema = ProposalSchema(session=db.session)
proposal_list_schema = ProposalSchema(many=True)


@proposal_bp.route('/from-job/<string:job_id>', methods=['POST'])
@login_required
def generate_proposal_from_job(job_id):
    try:
        # 1. Fetch the Upwork job
        job = UpworkJob.query.filter_by(job_id=job_id).first()
        if not job:
            return jsonify({"error": f"Upwork job with ID '{job_id}' not found"}), 404

        # 2. Prepare data for Gemini (cleaned + no duplicate keys)
        job_data = {
            "job_id": job.job_id,
            "title": job.title,
            "description": job.description,
            "skills": job.skills,
            "category": job.category,
            "budget": float(job.budget or 0),
            "budget_type": job.budget_type.value if job.budget_type else None,
            "project_length": job.project_length,
            "hours_per_week": job.hours_per_week,
            "client_country": job.client_country,
            "client_payment_verified": job.client_payment_verified,
            "client_total_spent": float(job.client_total_spent or 0),
            "client_jobs_posted": job.client_jobs_posted,
            "client_hire_rate": job.client_hire_rate,
            "connect_required": job.connect_required,
            "expected_cost": float(job.expected_cost or 0),
            "expected_earnings": float(job.expected_earnings or 0),
            "feasibility_status": job.feasibility_status.value if job.feasibility_status else None,
            "tags": job.tags,
            "posted_at": str(job.posted_at) if job.posted_at else None,
            "client_reviews": job.client_reviews,
            "proposals_submitted": job.proposals_submitted,
            "interviewing": job.interviewing,
            "invites_sent": job.invites_sent,
            "job_url": job.job_url
        }

        # 3. AI processing
        ai_result = assess_proposal_from_job(job_data)
        # print(ai_result)

        try:
            # parsed_data = extract_json_from_text(ai_result)
            parsed_data = ai_result
            print(parsed_data)
        except ValueError as e:
            print("Error:", e)

        # 4. Create proposal record
        proposal = Proposal(
            job_id=job.id,
            generated_by=current_user.id,
            cover_letter=parsed_data["cover_letter"],
            feasibility_score=parsed_data["feasibility_score"],
            feasibility_reason=parsed_data["feasibility_reason"],
            connects_required=job.connect_required,
            expected_cost=job.expected_cost,
            expected_earnings=job.expected_earnings,
            job_description=job.description,
            summary=parsed_data["summary"],
            project_duration=parsed_data["project_duration"],
            overall_score=parsed_data["overall_score"],
            tags=job.skills,
            status=ProposalStatusEnum.draft
        )

        db.session.add(proposal)
        db.session.commit()

        return jsonify({
            "message": "Proposal generated successfully using Gemini AI.",
            "proposal": proposal_schema.dump(proposal)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500





# from flask import Blueprint, request, jsonify
# from flask_login import login_required, current_user
# from app.extensions import db
# from app.models.proposal import Proposal
# from app.models.upwork_job import UpworkJob
# from app.schemas.proposal_schema import ProposalSchema
# from app.utils.gemini import assess_proposal_from_job  # <-- Your Gemini wrapper
# from app.enums import ProposalStatusEnum

# proposal_bp = Blueprint('proposal', __name__)

# proposal_schema = ProposalSchema(session=db.session)
# proposal_list_schema = ProposalSchema(many=True)


# @proposal_bp.route('/from-job/<string:job_id>', methods=['POST'])
# @login_required
# def generate_proposal_from_job(job_id):
#     try:
#         # 1. Fetch the Upwork job
#         job = UpworkJob.query.filter_by(job_id=job_id).first()
#         if not job:
#             return jsonify({"error": f"Upwork job with ID '{job_id}' not found"}), 404

#         # 2. Convert job to dict and send to Gemini
#         job_data = {
#             "job_id": job.job_id,
#             "title": job.title,
#             "description": job.description,
#             "skills": job.skills,
#             "category": job.category,
#             "budget": float(job.budget or 0),
#             "budget_type": job.budget_type.value if job.budget_type else None,
#             "project_length": job.project_length,
#             "hours_per_week": job.hours_per_week,
#             "client_country": job.client_country,
#             "client_payment_verified": job.client_payment_verified,
#             "client_total_spent": float(job.client_total_spent or 0),
#             "client_jobs_posted": job.client_jobs_posted,
#             "client_hire_rate": job.client_hire_rate,
#             "connect_required": job.connect_required,
#             "expected_cost": float(job.expected_cost or 0),
#             "expected_earnings": float(job.expected_earnings or 0),
#             "feasibility_status": job.feasibility_status,
#             "tags": job.tags,
#             "posted_at": str(job.posted_at),
#             "tags": job.tags,
#             "client_reviews": job.client_reviews,
#             "project_length": job.project_length,
#             "proposals_submitted": job.proposals_submitted,
#             "interviewing": job.interviewing,
#             "invites_sent": job.invites_sent,
#             "posted_at": job.posted_at,
#             "job_url": job.job_url
#         }

#         # 3. Ask Gemini to assess job and return proposal fields
#         ai_result = assess_proposal_from_job(job_data)  # This should return a dict

#         # 4. Create a Proposal instance
#         proposal = Proposal(
#             job_id=job.id,
#             generated_by=current_user.id,
#             cover_letter=ai_result.get("cover_letter"),
#             feasibility_score=ai_result.get("feasibility_score"),
#             feasibility_reason=ai_result.get("feasibility_reason"),
#             connects_required=job.connect_required,
#             expected_cost=job.expected_cost,
#             expected_earnings=job.expected_earnings,
#             job_description=job.description,
#             summary=ai_result.get("summary"),
#             project_duration=ai_result.get("project_duration"),
#             overall_score=ai_result.get("overall_score"),
#             tags=job.skills,
#             status=ProposalStatusEnum.draft
#         )

#         # 5. Save to DB
#         db.session.add(proposal)
#         db.session.commit()

#         return jsonify({
#             "message": "Proposal generated successfully using Gemini AI.",
#             "proposal": proposal_schema.dump(proposal)
#         }), 201

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": f"Internal server error: {str(e)}"}), 500
