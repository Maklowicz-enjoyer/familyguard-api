import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.routers.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

RECENT_MESSAGES_LIMIT = 40


def _verify_parent_paired_with_child(
    child_device_id: uuid.UUID, parent: models.User, db: Session
) -> None:
    pair = (
        db.query(models.DevicePair)
        .join(models.Device, models.DevicePair.guardian_device_id == models.Device.id)
        .filter(
            models.DevicePair.child_device_id == child_device_id,
            models.Device.user_id == parent.id,
            models.DevicePair.is_active.is_(True),
        )
        .first()
    )
    if not pair:
        raise HTTPException(status_code=403, detail="Brak aktywnego parowania z tym urządzeniem")


@router.get("/child/{child_device_id}", response_model=schemas.ChildDashboardResponse)
def get_child_dashboard(
    child_device_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != models.UserRole.parent:
        raise HTTPException(status_code=403, detail="Tylko konto rodzica może pobierać dashboard dziecka")

    _verify_parent_paired_with_child(child_device_id, current_user, db)

    child_device = db.query(models.Device).filter(models.Device.id == child_device_id).first()
    if not child_device:
        raise HTTPException(status_code=404, detail="Urządzenie nie istnieje")

    latest_location = (
        db.query(models.Location)
        .filter(models.Location.device_id == child_device_id)
        .order_by(models.Location.recorded_at.desc())
        .first()
    )

    recent_messages = (
        db.query(models.Message)
        .filter(
            (models.Message.sender_device_id == child_device_id) |
            (models.Message.receiver_device_id == child_device_id)
        )
        .order_by(models.Message.sent_at.desc())
        .limit(RECENT_MESSAGES_LIMIT)
        .all()
    )

    return schemas.ChildDashboardResponse(
        child_device_id=child_device.id,
        username=child_device.owner.username,
        device_name=child_device.device_name,
        last_seen=child_device.last_seen,
        latest_location=schemas.DashboardLocationResponse(
            latitude=float(latest_location.latitude),
            longitude=float(latest_location.longitude),
            accuracy_meters=float(latest_location.accuracy_meters) if latest_location.accuracy_meters is not None else None,
            battery_level=latest_location.battery_level,
            recorded_at=latest_location.recorded_at,
        ) if latest_location else None,
        recent_messages=[
            schemas.DashboardMessageResponse(
                id=msg.id,
                sender_device_id=msg.sender_device_id,
                receiver_device_id=msg.receiver_device_id,
                content=msg.content,
                sent_at=msg.sent_at,
                read_at=msg.read_at,
            )
            for msg in recent_messages
        ],
    )