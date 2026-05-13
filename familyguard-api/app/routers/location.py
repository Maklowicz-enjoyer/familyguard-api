import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.routers.auth import get_current_user

router = APIRouter(prefix="/location", tags=["location"])


def _get_device_or_403(device_id: uuid.UUID, user: models.User, db: Session) -> models.Device:
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Urządzenie nie istnieje")
    if device.user_id != user.id:
        raise HTTPException(status_code=403, detail="Brak dostępu do tego urządzenia")
    return device


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


@router.post("", response_model=schemas.LocationResponse, status_code=201)
def post_location(
    body: schemas.LocationCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != models.UserRole.child:
        raise HTTPException(status_code=403, detail="Tylko konto dziecka może wysyłać lokalizację")

    device = _get_device_or_403(body.device_id, current_user, db)

    pair = db.query(models.DevicePair).filter(
        models.DevicePair.child_device_id == device.id,
        models.DevicePair.is_active.is_(True),
    ).first()
    if not pair:
        raise HTTPException(status_code=403, detail="Urządzenie nie jest sparowane")

    location = models.Location(
        device_id=device.id,
        latitude=body.latitude,
        longitude=body.longitude,
        accuracy_meters=body.accuracy_meters,
        battery_level=body.battery_level,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return schemas.LocationResponse.model_validate(location)


@router.get("/{child_device_id}/latest", response_model=schemas.LocationResponse)
def get_latest_location(
    child_device_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != models.UserRole.parent:
        raise HTTPException(status_code=403, detail="Tylko konto rodzica może pobierać lokalizację")

    _verify_parent_paired_with_child(child_device_id, current_user, db)

    location = (
        db.query(models.Location)
        .filter(models.Location.device_id == child_device_id)
        .order_by(models.Location.recorded_at.desc())
        .first()
    )
    if not location:
        raise HTTPException(status_code=404, detail="Brak rekordów lokalizacji")

    return schemas.LocationResponse.model_validate(location)


@router.get("/{child_device_id}/history", response_model=list[schemas.LocationResponse])
def get_location_history(
    child_device_id: uuid.UUID,
    hours: int = Query(default=24, ge=1, le=48),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != models.UserRole.parent:
        raise HTTPException(status_code=403, detail="Tylko konto rodzica może pobierać historię lokalizacji")

    _verify_parent_paired_with_child(child_device_id, current_user, db)

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    locations = (
        db.query(models.Location)
        .filter(
            models.Location.device_id == child_device_id,
            models.Location.recorded_at >= since,
        )
        .order_by(models.Location.recorded_at.desc())
        .all()
    )
    return [schemas.LocationResponse.model_validate(loc) for loc in locations]