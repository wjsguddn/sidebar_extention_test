from fastapi import APIRouter, Request
from pydantic import BaseModel
from confluent_kafka import Producer
import json, os

collect_browser_router = APIRouter()

BOOT = os.getenv("KAFKA_BOOTSTRAP")
producer = Producer({"bootstrap.servers": BOOT})

class CollectReq(BaseModel):
    url: str
    title: str
    text: str
    screenshot_base64: str = ""

@collect_browser_router.post("/collect/browser")
async def collect_browser(req: CollectReq, request: Request):
    body = await request.json()
    trigger_type = body.get("trigger_type", "unknown")
    print(f"[COLLECT] trigger_type={trigger_type} url={req.url}", flush=True)
    producer.produce("collect.browser", json.dumps(req.model_dump()).encode())
    producer.flush()
    return {"status": "queued"} 