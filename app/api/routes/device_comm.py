from datetime import timedelta
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_device
from app.models.entities import Device,DeviceCommand,Visitor,VisitorCredential,FingerprintEnrollment,AccessRequest,EntryLog
from app.schemas.resources import CommandAck,AuthEvent
from app.core.security import verify_password
from app.services.common import utcnow
router=APIRouter(prefix='/device',tags=['Device Communication'])
@router.post('/heartbeat')
def heartbeat(firmware_version:str|None=None,device=Depends(current_device),db:Session=Depends(get_db)):
    device.status='online'; device.last_heartbeat_at=utcnow()
    if firmware_version: device.firmware_version=firmware_version
    db.commit(); return {'status':'online','server_time':utcnow()}
@router.get('/config')
def config(device=Depends(current_device)):
    return {'device_id':str(device.id),'heartbeat_interval_seconds':20,'command_poll_interval_seconds':1,'supported_authentication':['fingerprint','pin'],'display_messages':['access_granted','access_denied','fingerprint_not_recognized','pin_incorrect','waiting_for_owner_approval','please_try_again','system_offline']}
@router.get('/commands')
def commands(device=Depends(current_device),db:Session=Depends(get_db)):
    rows=db.query(DeviceCommand).filter(DeviceCommand.device_id==device.id,DeviceCommand.status.in_(['pending','delivered']),DeviceCommand.expires_at>utcnow(),((DeviceCommand.status=='pending') | (DeviceCommand.created_at<=utcnow()-timedelta(seconds=10)))).order_by(DeviceCommand.created_at).with_for_update(skip_locked=True).limit(20).all()
    for c in rows: c.status='delivered'
    db.commit(); return [{'id':str(c.id),'command_type':c.command_type,'payload':c.payload,'expires_at':c.expires_at} for c in rows]

@router.post('/commands/{command_id}/ack')
def acknowledge(
    command_id: str,
    data: CommandAck,
    device=Depends(current_device),
    db: Session = Depends(get_db)
):
    c = db.query(DeviceCommand).filter_by(
        id=command_id,
        device_id=device.id
    ).first()

    if not c:
        raise HTTPException(404, 'Command not found')

    if c.status == 'acknowledged':
        return {'message': 'Already acknowledged'}

    if data.status not in ('success', 'failed'):
        raise HTTPException(400, 'Invalid command status')

    # Handle fingerprint deletion confirmation.
    if c.command_type == 'fingerprint_delete':
        template_id = c.payload.get('template_id')

        rec = db.query(FingerprintEnrollment).filter_by(
            device_id=device.id,
            template_id=template_id
        ).first()

        if rec:
            if data.status == 'success':
                db.delete(rec)
            else:
                rec.status = 'active'

    c.status = 'acknowledged'
    c.acknowledged_at = utcnow()
    c.result = data.result

    db.commit()

    return {
        'message': 'Command acknowledgement recorded',
        'status': data.status
    }

@router.post('/authenticate')
def authenticate(data:AuthEvent,device=Depends(current_device),db:Session=Depends(get_db)):
    method=data.method.lower(); visitor=None; success=False
    if method=='pin' and data.pin:
        creds=db.query(VisitorCredential).filter_by(tenant_id=device.tenant_id).all()
        for cred in creds:
            if verify_password(data.pin,cred.pin_hash): visitor=db.query(Visitor).filter_by(id=cred.visitor_id,tenant_id=device.tenant_id,is_active=True).first(); success=visitor is not None; break
    elif method=='fingerprint' and data.template_id is not None:
        mapping=db.query(FingerprintEnrollment).filter_by(device_id=device.id,template_id=data.template_id,status='active').first()
        if mapping: visitor=db.query(Visitor).filter_by(id=mapping.visitor_id,tenant_id=device.tenant_id,is_active=True).first(); success=visitor is not None
    else: raise HTTPException(422,'Provide method pin with pin, or fingerprint with template_id')
    log=EntryLog(tenant_id=device.tenant_id,visitor_id=visitor.id if visitor else None,device_id=device.id,authentication_method=method,authentication_result='success' if success else 'failed',access_decision='pending' if success else 'not_applicable',metadata_json={})
    db.add(log)
    if not success: db.commit(); return {'authenticated':False,'message':'PIN incorrect' if method=='pin' else 'Fingerprint not recognized'}
    req=AccessRequest(tenant_id=device.tenant_id,visitor_id=visitor.id,device_id=device.id,authentication_method=method,status='pending',expires_at=utcnow()+timedelta(minutes=2)); db.add(req); db.commit()
    return {'authenticated':True,'visitor_id':str(visitor.id),'visitor_name':visitor.name,'access_request_id':str(req.id),'status':'waiting_for_owner_approval'}
