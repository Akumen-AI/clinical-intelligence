from datetime import datetime, timezone, timedelta
import time
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.database import get_db
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
    SECRET_KEY,
    ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS
)

from app.core.rate_limit import limiter

router = APIRouter()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    message: str = "Authenticated successfully"

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(login_data: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    now = time.time()

    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not user.password_hash or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Encode only the principal
    payload = {"sub": str(user.id)}
    
    access_token = create_access_token(payload)
    refresh_token, jti = create_refresh_token(payload)
    
    # Store refresh token in DB
    db_token = RefreshToken(
        user_id=user.id,
        token_jti=jti,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(db_token)
    db.commit()

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60*24*60 # 24 hours
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS*24*60*60
    )
    
    return TokenResponse()

@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
            
        user_id_str = payload.get("sub")
        jti = payload.get("jti")
        if not user_id_str or not jti:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
            
        db_token = db.query(RefreshToken).filter(RefreshToken.token_jti == jti).first()
        if not db_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found")
            
        if db_token.revoked:
            # Reuse detected! Revoke all tokens for this user as a security measure
            db.query(RefreshToken).filter(RefreshToken.user_id == db_token.user_id).update({"revoked": True})
            db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")
            
        expires_at = db_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")
            
        # Revoke the old token (rotation)
        db_token.revoked = True
        
        # Issue new tokens
        new_payload = {"sub": user_id_str}
        access_token = create_access_token(new_payload)
        new_refresh_token, new_jti = create_refresh_token(new_payload)
        
        new_db_token = RefreshToken(
            user_id=db_token.user_id,
            token_jti=new_jti,
            expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        )
        db.add(new_db_token)
        db.commit()
        
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=60*24*60
        )
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=REFRESH_TOKEN_EXPIRE_DAYS*24*60*60
        )
        return TokenResponse()
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

@router.post("/logout", response_model=TokenResponse)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            jti = payload.get("jti")
            if jti:
                db_token = db.query(RefreshToken).filter(RefreshToken.token_jti == jti).first()
                if db_token:
                    db_token.revoked = True
                    db.commit()
        except JWTError:
            pass
            
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return TokenResponse(message="Logged out")

class UserProfileResponse(BaseModel):
    id: str
    email: str
    role: str
    patient_access: list[str]

@router.get("/me", response_model=UserProfileResponse)
def get_me(current_user: User = Depends(get_current_user)):
    # Since get_current_user now fetches from DB, current_user reflects live DB state
    return UserProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        role=current_user.role,
        patient_access=current_user.patient_access
    )
