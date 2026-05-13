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
    device = models.Device(
        user_id=current_user.id,
        device_name=body.device_name,
        platform=body.platform,
        fcm_token=body.fcm_token,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return schemas.DeviceResponse.model_validate(device)