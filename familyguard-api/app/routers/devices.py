import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.routers.auth import get_current_user

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/register", response_model=schemas.DeviceResponse, status_code=201)
def register_device(
    body: schemas.DeviceRegisterRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Jeśli hardware_id podany — sprawdź czy urządzenie już istnieje
    if body.hardware_id:
        existing = db.query(models.Device).filter(
            models.Device.user_id == current_user.id,
            models.Device.hardware_id == body.hardware_id,
        ).first()

        if existing:
            # Zaktualizuj dane urządzenia i zwróć istniejący device_id
            existing.device_name = body.device_name
            existing.fcm_token = body.fcm_token
            existing.platform = body.platform
            db.commit()
            db.refresh(existing)
            return schemas.DeviceResponse.model_validate(existing)

    device = models.Device(
        user_id=current_user.id,
        device_name=body.device_name,
        platform=body.platform,
        fcm_token=body.fcm_token,
        hardware_id=body.hardware_id,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return schemas.DeviceResponse.model_validate(device)