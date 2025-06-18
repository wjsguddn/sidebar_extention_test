from fastapi import FastAPI
from pydantic import BaseModel
from confluent_kafka import Producer
import json, os

app = FastAPI()

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
producer = Producer({"bootstrap.servers": BOOTSTRAP})

class RecommendRequest(BaseModel):
    url: str
    title: str
    text: str
    screenshot_base64: str

@app.post("/collect")
async def collect_browser_data(req: RecommendRequest):
    data = req.model_dump()        # pydantic v2 호환
    print("POST 요청 수신:", data["url"])
    producer.produce("browser.events", json.dumps(data).encode())
    producer.flush()
    return {"status": "queued"}
