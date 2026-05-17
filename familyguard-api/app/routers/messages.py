import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.routers.auth import get_current_user

router = APIRouter(prefix="/messages", tags=["messages"])


def _get_device_or_403(device_id: uuid.UUID, user: models.User, db: Session) -> models.Device:
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Urządzenie nie istnieje")
    if device.user_id != user.id:
        raise HTTPException(status_code=403, detail="Brak dostępu do tego urządzenia")
    return device


def _verify_devices_paired(sender_id: uuid.UUID, receiver_id: uuid.UUID, db: Session) -> None:
    pair = db.query(models.DevicePair).filter(
        (
            (models.DevicePair.child_device_id == sender_id) &
            (models.DevicePair.guardian_device_id == receiver_id)
        ) | (
            (models.DevicePair.child_device_id == receiver_id) &
            (models.DevicePair.guardian_device_id == sender_id)
        ),
        models.DevicePair.is_active.is_(True),
    ).first()
    if not pair:
        raise HTTPException(status_code=403, detail="Urządzenia nie są sparowane")


@router.post("", response_model=schemas.MessageResponse, status_code=201)
def send_message(
    body: schemas.MessageSendRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_device_or_403(body.sender_device_id, current_user, db)
    _verify_devices_paired(body.sender_device_id, body.receiver_device_id, db)

    message = models.Message(
        sender_device_id=body.sender_device_id,
        receiver_device_id=body.receiver_device_id,
        content=body.content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return schemas.MessageResponse.model_validate(message)


@router.get("/history", response_model=list[schemas.MessageResponse])
def get_message_history(
    device_id: uuid.UUID,
    limit: int = Query(default=40, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_device_or_403(device_id, current_user, db)

    messages = (
        db.query(models.Message)
        .filter(
            (models.Message.sender_device_id == device_id) |
            (models.Message.receiver_device_id == device_id)
        )
        .order_by(models.Message.sent_at.desc())
        .limit(limit)
        .all()
    )
    return [schemas.MessageResponse.model_validate(msg) for msg in messages]


@router.post("/{message_id}/read", response_model=schemas.MessageResponse)
def mark_as_read(
    message_id: uuid.UUID,
    device_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_device_or_403(device_id, current_user, db)

    message = db.query(models.Message).filter(models.Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Wiadomość nie istnieje")
    if message.receiver_device_id != device_id:
        raise HTTPException(status_code=403, detail="Tylko odbiorca może oznaczyć wiadomość jako przeczytaną")

    if message.read_at is None:
        message.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(message)

    return schemas.MessageResponse.model_validate(message)