from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import requests as py_requests
import os, jwt
import hashlib
import secrets
from datetime import datetime, timedelta

from ..db import get_db
from ..models import User, RefreshToken

auth_google_router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
EXTENSION_ID = os.getenv("EXTENSION_ID")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

def get_or_create_user(db, email, sub, name=None, picture=None):
    user = db.query(User).filter(User.id == sub).first()
    if not user:
        user = User(id=sub, email=email, name=name, picture=picture)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # 프로필 정보 갱신
        updated = False
        if user.name != name:
            user.name = name
            updated = True
        if user.picture != picture:
            user.picture = picture
            updated = True
        if updated:
            db.commit()
            db.refresh(user)
    return user

def hash_token(token: str) -> str:
    """토큰을 SHA-256으로 해시화"""
    hash_object = hashlib.sha256(token.encode('utf-8'))
    return hash_object.hexdigest()

def create_access_token(user: User) -> str:
    """Access token 생성 (1시간)"""
    payload = {
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "type": "access",
        "exp": datetime.utcnow() + timedelta(hours=1),  # 1시간으로 변경
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

def create_refresh_token(user: User) -> str:
    """Refresh token 생성 (30일)"""
    payload = {
        "user_id": user.id,
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=30),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

def save_refresh_token(user_id: str, refresh_token: str, db: Session):
    """Refresh token을 해시화하여 DB에 저장"""
    token_hash = hash_token(refresh_token)
    payload = jwt.decode(refresh_token, JWT_SECRET_KEY, algorithms=["HS256"])
    expires_at = datetime.utcfromtimestamp(payload["exp"])
    
    refresh_token_record = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        is_revoked=False
    )
    
    db.add(refresh_token_record)
    db.commit()
    return refresh_token_record

@auth_google_router.post("/auth/google")
async def google_auth(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    code = body.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is required")

    # 구글 토큰 교환
    token_data = {
        'code': code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': f'https://{EXTENSION_ID}.chromiumapp.org/',
        'grant_type': 'authorization_code'
    }
    token_resp = py_requests.post('https://oauth2.googleapis.com/token', data=token_data)
    if not token_resp.ok:
        print("Google token exchange error:", token_resp.text)
        raise HTTPException(status_code=400, detail="Failed to exchange code for token")
    tokens = token_resp.json()
    id_token_str = tokens.get('id_token')
    if not id_token_str:
        raise HTTPException(status_code=400, detail="No id_token in Google response")

    # id_token 검증 및 사용자 정보 추출
    try:
        idinfo = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id_token")

    email = idinfo.get("email")
    sub = idinfo.get("sub")
    name = idinfo.get("name")
    picture = idinfo.get("picture")

    if not email or not sub:
        raise HTTPException(status_code=400, detail="Invalid user info")

    # DB에서 사용자 조회/생성
    user = get_or_create_user(db, email, sub, name, picture)

    # JWT 발급
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    save_refresh_token(user.id, refresh_token, db)

    return {"access_token": access_token, "refresh_token": refresh_token}

@auth_google_router.post("/auth/refresh")
async def refresh_token(request: Request, db: Session = Depends(get_db)):
    """Refresh token으로 새로운 access token 발급"""
    body = await request.json()
    refresh_token = body.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token required")
    
    try:
        # 1. JWT 자체 검증
        payload = jwt.decode(refresh_token, JWT_SECRET_KEY, algorithms=["HS256"])
        
        # 2. 토큰 타입 확인
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        # 3. 만료 확인
        if datetime.utcfromtimestamp(payload["exp"]) < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Token expired")
        
        # 4. DB에서 토큰 무효화 여부 확인
        user_id = payload.get("user_id")
        token_hash = hash_token(refresh_token)
        
        token_record = db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        ).first()
        
        if not token_record:
            raise HTTPException(status_code=401, detail="Token revoked or not found")
        
        # 5. 새로운 Access Token 발급
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        new_access_token = create_access_token(user)
        
        return {"access_token": new_access_token}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@auth_google_router.post("/auth/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    """로그아웃 - refresh token 무효화"""
    body = await request.json()
    refresh_token = body.get("refresh_token")
    
    if refresh_token:
        try:
            token_hash = hash_token(refresh_token)
            token_record = db.query(RefreshToken).filter(
                RefreshToken.token_hash == token_hash
            ).first()
            
            if token_record:
                token_record.is_revoked = True
                db.commit()
        
        except Exception:
            pass  # 토큰이 유효하지 않아도 로그아웃은 성공으로 처리
    
    return {"message": "Logged out successfully"}