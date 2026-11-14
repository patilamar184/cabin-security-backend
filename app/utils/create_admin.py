import os
from app.db.session import SessionLocal
from app.models.entities import PlatformAdmin
from app.core.security import hash_password
def main():
    email=os.environ['ADMIN_EMAIL'].lower(); password=os.environ['ADMIN_PASSWORD']
    db=SessionLocal()
    try:
        if db.query(PlatformAdmin).filter_by(email=email).first(): print('Admin already exists'); return
        db.add(PlatformAdmin(email=email,password_hash=hash_password(password))); db.commit(); print('Platform admin created')
    finally: db.close()
if __name__=='__main__': main()
