from fastapi import APIRouter, WebSocket, Query
from ..websocket_manager import websocket_manager
from jose import jwt, JWTError
import os

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")  # 환경변수에서 불러오기

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    # JWT에서 user_id 추출
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = str(payload.get("user_id"))
        if not user_id:
            await websocket.close()
            return
    except JWTError:
        await websocket.close()
        return

    await websocket_manager.connect(websocket, user_id=user_id)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        websocket_manager.disconnect(websocket, user_id=user_id)