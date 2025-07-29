from fastapi import APIRouter, Request, Header, HTTPException
from pydantic import BaseModel
import json, os, jwt

from ..grpc_clients.rec_client import RecClient
from ..websocket_manager import websocket_manager


collect_browser_router = APIRouter()
rec_client = RecClient()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

class CollectReq(BaseModel):
    url: str
    title: str
    text: str
    screenshot_base64: str = ""

@collect_browser_router.post("/collect/browser")
async def collect_browser(req: CollectReq,
                          request: Request,
                          authorization: str = Header(None)):
    # JWT 추출 및 decode
    if not authorization or not authorization.startswith("Bearer "):
        print("401 Unauthorized: Authorization header missing or invalid")
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if not user_id:
            print("401 Unauthorized: user_id not found in token")
            raise HTTPException(status_code=401, detail="user_id not found in token")
    except jwt.ExpiredSignatureError:
        print("401 Unauthorized: Token expired")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        print("401 Unauthorized: Invalid token")
        raise HTTPException(status_code=401, detail="Invalid token")

    # trigger_type 추출
    body = await request.json()
    trigger_type = body.get("trigger_type", "unknown")
    print(f"[COLLECT BROWSER] trigger_type={trigger_type} url={req.url}", flush=True)


    data = req.model_dump()

    # gRPC Recommend stream 호출 및 WebSocket 전송
    async for chunk in rec_client.recommend_stream(user_id, json.dumps(data)):
        print(chunk, flush=True)
        await websocket_manager.send_to_user(user_id, {
            "type": "browser",
            "content": chunk.content,
            "is_final_b": chunk.is_final
        })

    return {"status": "ok"}
