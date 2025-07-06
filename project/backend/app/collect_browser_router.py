from fastapi import APIRouter, Request, Header, HTTPException
from pydantic import BaseModel
from confluent_kafka import Producer
import json, os, jwt

collect_browser_router = APIRouter()

BOOT = os.getenv("KAFKA_BOOTSTRAP")
producer = Producer({"bootstrap.servers": BOOT})

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")  # 환경변수에서 관리

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
    print(f"[COLLECT] trigger_type={trigger_type} url={req.url}", flush=True)

    # Kafka로 user_id 포함해서 전송
    kafka_data = req.model_dump()
    kafka_data["user_id"] = user_id
    producer.produce("collect.browser", json.dumps(kafka_data).encode())
    producer.flush()
    return {"status": "queued"}