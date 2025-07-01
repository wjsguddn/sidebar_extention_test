# app/main.py
from fastapi import FastAPI, Request
from pydantic import BaseModel
from confluent_kafka import Producer
import json, os

app = FastAPI()

BOOT = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")   # dev=compose, prod=env
producer = Producer({"bootstrap.servers": BOOT})

class CollectReq(BaseModel):
    url: str
    title: str
    text: str
    screenshot_base64: str = ""

# ----------브라우저 정보 수집
@app.post("/collect")
async def collect(req: CollectReq, request: Request):
    body = await request.json()
    trigger_type = body.get("trigger_type", "unknown")
    print(f"[COLLECT] trigger_type={trigger_type} url={req.url}", flush=True)
    producer.produce("browser.events", json.dumps(req.model_dump()).encode())
    producer.flush()
    return {"status": "queued"}

# ----------추천 결과 반환 (추후 LLM 호출)
@app.get("/recommend")
async def recommend(url: str):
    """URL 1개에 대한 추천 결과 임시 모킹"""
    return {"url": url, "recommend": ["추천 A", "추천 B", "추천 C", "추천 D", "추천 E"]}
