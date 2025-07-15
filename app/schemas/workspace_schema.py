from marshmallow_sqlalchemy import SQLAlchemySchema, auto_field
from app.models.workspace import Workspace

class WorkspaceSchema(SQLAlchemySchema):
    class Meta:
        model = Workspace
        load_instance = True

    id = auto_field(dump_only=True)
    name = auto_field(required=True, error_messages={"required": "Workspace name is required."})
    description = auto_field()
    invite_code = auto_field(required=True, error_messages={"required": "Invite code is required."})
    created_at = auto_field(dump_only=True)
