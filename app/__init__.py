from flask import Flask
from app.config import Config
from app.extensions import db, migrate
from app.routes.auth_routes import auth_bp
from app.routes.user_routes import user_bp
from app.routes.scrap_routes import scraper_bp
from app.routes.workspace_routes import workspace_bp
from flask_login import LoginManager
from flask import jsonify


login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    login_manager.login_view = 'auth.login'  # 'auth' = blueprint name, 'login' = function name
    login_manager.login_message = "Please log in to access website."

    # Custom unauthorized handler
    @login_manager.unauthorized_handler
    def unauthorized_callback():
        return jsonify({"error": "You must be logged in to access this resource."}), 401

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
    app.register_blueprint(scraper_bp, url_prefix='/api/scrape')
    app.register_blueprint(workspace_bp, url_prefix='/api/workspaces')


    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app