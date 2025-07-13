from app.extensions import db
from datetime import datetime, timezone


class Workspace(db.Model):
    __tablename__ = 'workspaces'

    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.String(100), nullable=False)  # e.g., "Frontend"
    description = db.Column(db.Text, nullable=True)
    
    invite_code = db.Column(db.String(50), unique=True, nullable=False)
    
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Workspace {self.id} - {self.name}>"