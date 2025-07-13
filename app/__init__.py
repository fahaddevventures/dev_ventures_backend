from flask import Flask
from app.config import Config
from app.extensions import db, migrate
from app.routes.auth_routes import auth_bp
from app.routes.user_routes import user_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    # Import all models here to register with SQLAlchemy
    from app.models.user import User
    from app.models.skill import Skill
    from app.models.user_skill import UserSkill
    from app.models.upwork_job import UpworkJob
    from app.models.upwork_profile import UpworkProfile
    from app.models.proposal import Proposal
    from app.models.workspace import Workspace
    from app.models.project import Project
    from app.models.project_member import ProjectMember
    from app.models.task import Task
    from app.models.task_deliverable import TaskDeliverable
    from app.models.task_attachment import TaskAttachment
    from app.models.project_attachment import ProjectAttachment

    # Register Blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/users')

    return app