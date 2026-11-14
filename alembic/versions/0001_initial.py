"""Initial schema generated from SQLAlchemy metadata."""
from alembic import op
from app.db.base import Base
from app.models import entities
revision='0001_initial'
down_revision=None
branch_labels=None
depends_on=None
def upgrade(): Base.metadata.create_all(bind=op.get_bind())
def downgrade(): Base.metadata.drop_all(bind=op.get_bind())
