from app.extensions import db
from datetime import datetime, timezone

class ProjectMember(db.Model):
    __tablename__ = 'project_members'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)

    role_in_project = db.Column(db.String(100), nullable=True)  # e.g., "frontend dev", "QA", etc.
    joined_at =  db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('project_memberships', cascade='all, delete-orphan'))
    project = db.relationship('Project', backref=db.backref('members', cascade='all, delete-orphan'))

    def __repr__(self):
        return f"<ProjectMember user_id={self.user_id}, project_id={self.project_id}>"