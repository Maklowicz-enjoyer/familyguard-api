import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.routers.auth import get_current_user

router = APIRouter(prefix="/sos", tags=["sos"])


@router.post("", response_model=schemas.SosAlertResponse, status_code=201)
def send_sos(
    body: schemas.SosRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != models.UserRole.child:
        raise HTTPException(status_code=403, detail="Tylko konto dziecka może wysłać SOS")

    device = db.query(models.Device).filter(models.Device.id == body.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Urządzenie nie istnieje")
    if device.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Brak dostępu do tego urządzenia")

    pair = db.query(models.DevicePair).filter(
        models.DevicePair.child_device_id == body.device_id,
        models.DevicePair.is_active.is_(True),
    ).first()
    if not pair:
        raise HTTPException(status_code=403, detail="Urządzenie nie jest sparowane")

    alert = models.SosAlert(child_device_id=body.device_id)
    db.add(alert)
    db.commit()
    db.refresh(alert)

    return schemas.SosAlertResponse(
        id=alert.id,
        child_device_id=alert.child_device_id,
        child_username=current_user.username,
        created_at=alert.created_at,
        acknowledged_at=alert.acknowledged_at,
    )


@router.get("/pending", response_model=list[schemas.SosAlertResponse])
def get_pending_sos(
    device_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != models.UserRole.parent:
        raise HTTPException(status_code=403, detail="Tylko konto rodzica może sprawdzać alerty SOS")

    guardian_device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not guardian_device:
        raise HTTPException(status_code=404, detail="Urządzenie nie istnieje")
    if guardian_device.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Brak dostępu do tego urządzenia")

    pairs = db.query(models.DevicePair).filter(
        models.DevicePair.guardian_device_id == device_id,
        models.DevicePair.is_active.is_(True),
    ).all()

    child_device_ids = [pair.child_device_id for pair in pairs]
    if not child_device_ids:
        return []

    alerts = (
        db.query(models.SosAlert)
        .options(joinedload(models.SosAlert.child_device).joinedload(models.Device.owner))
        .filter(
            models.SosAlert.child_device_id.in_(child_device_ids),
            models.SosAlert.acknowledged_at.is_(None),
        )
        .order_by(models.SosAlert.created_at.desc())
        .all()
    )

    return [
        schemas.SosAlertResponse(
            id=alert.id,
            child_device_id=alert.child_device_id,
            child_username=alert.child_device.owner.username,
            created_at=alert.created_at,
            acknowledged_at=alert.acknowledged_at,
        )
        for alert in alerts
    ]


@router.post("/{sos_id}/acknowledge", response_model=schemas.SosAcknowledgeResponse)
def acknowledge_sos(
    sos_id: uuid.UUID,
    device_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != models.UserRole.parent:
        raise HTTPException(status_code=403, detail="Tylko konto rodzica może potwierdzić SOS")

    guardian_device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not guardian_device or guardian_device.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Brak dostępu do tego urządzenia")

    alert = (
        db.query(models.SosAlert)
        .join(models.DevicePair, models.SosAlert.child_device_id == models.DevicePair.child_device_id)
        .filter(
            models.SosAlert.id == sos_id,
            models.DevicePair.guardian_device_id == device_id,
            models.DevicePair.is_active.is_(True),
        )
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert SOS nie istnieje")

    if alert.acknowledged_at is None:
        alert.acknowledged_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(alert)

    return schemas.SosAcknowledgeResponse(
        id=alert.id,
        acknowledged_at=alert.acknowledged_at,
    )