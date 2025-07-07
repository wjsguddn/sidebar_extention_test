from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import requests as py_requests
import os, jwt
from datetime import datetime, timedelta

from ..db import get_db
from ..models import User

auth_google_router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
EXTENSION_ID = os.getenv("EXTENSION_ID")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

def get_or_create_user(db, email, sub):
    user = db.query(User).filter(User.id == sub).first()
    if not user:
        user = User(id=sub, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

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
    if not email or not sub:
        raise HTTPException(status_code=400, detail="Invalid user info")

    # DB에서 사용자 조회/생성
    user = get_or_create_user(db, email, sub)

    # JWT 발급
    jwt_payload = {
        "user_id": user.id,
        "email": user.email,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    my_jwt = jwt.encode(jwt_payload, JWT_SECRET_KEY, algorithm="HS256")

    return {"token": my_jwt, "user": {"id": user.id, "email": user.email}}