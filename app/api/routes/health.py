from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import get_db
router=APIRouter(tags=['Health'])
@router.get('/health')
def health(): return {'status':'ok'}
@router.get('/health/database')
def database_health(db:Session=Depends(get_db)):
    try: db.execute(text('SELECT 1')); return {'status':'ok','database':'connected'}
    except Exception: raise HTTPException(503,'Database unavailable')
