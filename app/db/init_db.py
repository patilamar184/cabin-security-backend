from app.db.base import Base
from app.db.session import engine
from app.models import entities
def init_db(): Base.metadata.create_all(bind=engine)
if __name__=='__main__': init_db(); print('Database tables created')
