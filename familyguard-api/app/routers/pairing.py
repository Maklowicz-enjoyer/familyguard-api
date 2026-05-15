import uuid
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.routers.auth import get_current_user
from sqlalchemy.orm import Session, joinedload

router = APIRouter(prefix="/pairing", tags=["pairing"])


def _get_device_or_403(
    device_id: uuid.UUID,
    user: models.User,
    db: Session,
) -> models.Device:
    """Pobiera urządzenie i weryfikuje że należy do zalogowanego użytkownika."""
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Urządzenie nie istnieje")
    if device.user_id != user.id:
        raise HTTPException(status_code=403, detail="Brak dostępu do tego urządzenia")
    return device


@router.post("/generate", response_model=schemas.PairingCodeResponse, status_code=201)
def generate_pairing_code(
    body: schemas.GeneratePairingCodeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != models.UserRole.child:
        raise HTTPException(status_code=403, detail="Tylko konto dziecka może generować kod")

    device = _get_device_or_403(body.device_id, current_user, db)

    # Unieważnij poprzednie nieużyte kody dla tego urządzenia
    db.query(models.PairingCode).filter(
        models.PairingCode.child_device_id == device.id,
        models.PairingCode.used_at.is_(None),
    ).update({"used_at": datetime.now(timezone.utc)})

    code = str(secrets.randbelow(1_000_000)).zfill(6)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    pairing_code = models.PairingCode(
        child_device_id=device.id,
        code=code,
        expires_at=expires_at,
    )
    db.add(pairing_code)
    db.commit()
    db.refresh(pairing_code)
    return schemas.PairingCodeResponse.model_validate(pairing_code)


@router.post("/confirm", response_model=schemas.DevicePairResponse)
def confirm_pairing(
    body: schemas.ConfirmPairingRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != models.UserRole.parent:
        raise HTTPException(status_code=403, detail="Tylko konto rodzica może potwierdzić parowanie")

    guardian_device = _get_device_or_403(body.guardian_device_id, current_user, db)

    # Szukaj kodu
    pairing_code = db.query(models.PairingCode).filter(
        models.PairingCode.code == body.code,
        models.PairingCode.used_at.is_(None),
        models.PairingCode.expires_at > datetime.now(timezone.utc),
    ).first()

    if not pairing_code:
        raise HTTPException(status_code=404, detail="Kod nieprawidłowy lub wygasł")

    # Sprawdź czy para już istnieje
    existing_pair = db.query(models.DevicePair).filter(
        models.DevicePair.child_device_id == pairing_code.child_device_id,
        models.DevicePair.guardian_device_id == guardian_device.id,
        models.DevicePair.is_active.is_(True),
    ).first()
    if existing_pair:
        raise HTTPException(status_code=409, detail="Urządzenia są już sparowane")

    # Unieważnij kod
    pairing_code.used_at = datetime.now(timezone.utc)

    # Stwórz parę
    pair = models.DevicePair(
        child_device_id=pairing_code.child_device_id,
        guardian_device_id=guardian_device.id,
    )
    db.add(pair)
    db.commit()
    db.refresh(pair)
    return schemas.DevicePairResponse.model_validate(pair)

@router.get("/my-children", response_model=list[schemas.ChildInfoResponse])
def get_my_children(
    device_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_device_or_403(device_id, current_user, db)

    pairs = (
        db.query(models.DevicePair)
        .options(
            joinedload(models.DevicePair.child_device).joinedload(models.Device.owner)
        )
        .filter(
            models.DevicePair.guardian_device_id == device_id,
            models.DevicePair.is_active.is_(True),
        )
        .all()
    )

    return [
        schemas.ChildInfoResponse(
            pair_id=pair.id,
            child_device_id=pair.child_device.id,
            child_user_id=pair.child_device.owner.id,
            username=pair.child_device.owner.username,
            device_name=pair.child_device.device_name,
            last_seen=pair.child_device.last_seen,
            paired_at=pair.paired_at,
        )
        for pair in pairs
    ]


@router.get("/my-guardian", response_model=schemas.GuardianInfoResponse)
def get_my_guardian(
    device_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_device_or_403(device_id, current_user, db)

    pair = db.query(models.DevicePair).filter(
        models.DevicePair.child_device_id == device_id,
        models.DevicePair.is_active.is_(True),
    ).first()

    if not pair:
        raise HTTPException(status_code=404, detail="Urządzenie nie jest sparowane")

    guardian_device = pair.guardian_device
    guardian_user = guardian_device.owner
    return schemas.GuardianInfoResponse(
        pair_id=pair.id,
        guardian_device_id=guardian_device.id,
        guardian_user_id=guardian_user.id,
        username=guardian_user.username,
        device_name=guardian_device.device_name,
        paired_at=pair.paired_at,
    )

@router.get("/status", response_model=schemas.PairingStatusResponse)
def pairing_status(
    device_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    device = _get_device_or_403(device_id, current_user, db)

    pair = db.query(models.DevicePair).filter(
        (models.DevicePair.child_device_id == device.id) |
        (models.DevicePair.guardian_device_id == device.id),
        models.DevicePair.is_active.is_(True),
    ).first()

    if not pair:
        return schemas.PairingStatusResponse(is_paired=False)

    return schemas.PairingStatusResponse(
        is_paired=True,
        pair_id=str(pair.id),
        paired_at=pair.paired_at,
    )