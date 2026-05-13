
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app import models, schemas, security
from app.database import get_db
from jose import JWTError

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer()

@router.post("/register", response_model=schemas.UserResponse, status_code=201)
def register(body: schemas.RegisterRequest, db: Session = Depends(get_db)):
    # Sprawdzamy czy email już istnieje
    existing = db.query(models.User).filter(models.User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email już zajęty")

    user = models.User(
        email=body.email,
        password_hash=security.hash_password(body.password),
        username=body.username,
        role=models.UserRole[body.role.value],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return schemas.UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        role=user.role.value,
    )

@router.post("/login", response_model=schemas.TokenResponse)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == body.email).first()
   
    if not user or not security.verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Nieprawidłowe dane logowania")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Konto nieaktywne")

    token = security.create_access_token(str(user.id), user.role.value)
    return schemas.TokenResponse(access_token=token)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    # weryfikuje JWT i zwraca obiekt użytkownika lub rzuca 401 jeśli token jest nieważny lub wygasł
    try:
        payload = security.decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Nieprawidłowy token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token nieważny lub wygasł")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Użytkownik nie istnieje")
    return user

@router.get("/me", response_model=schemas.UserResponse)
def me(current_user: models.User = Depends(get_current_user)):
    return schemas.UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        role=current_user.role.value,
    )