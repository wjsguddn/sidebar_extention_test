import threading
import json, os
# import time
from confluent_kafka import Consumer
from .result_handlers.browser import handle_browser_result
from .result_handlers.document import handle_document_result
from .result_handlers.youtube import handle_youtube_result

BOOT = os.getenv("KAFKA_BOOTSTRAP")

def consume_result_topics():
    consumer = Consumer({
        "bootstrap.servers": BOOT,
        "group.id": "fastapi-result-consumer",
        "auto.offset.reset": "latest"
    })
    consumer.subscribe(["result.browser", "result.document", "result.youtube"])
    # print("result.* 토픽 구독 시작")
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print("Kafka error:", msg.error())
            continue
        try:
            result = json.loads(msg.value().decode())
            topic = msg.topic()
            if topic == "result.browser":
                handle_browser_result(result)
            elif topic == "result.document":
                handle_document_result(result)
            elif topic == "result.youtube":
                handle_youtube_result(result)
            else:
                print(f"알 수 없는 토픽: {topic}")
        except Exception as e:
            print("메시지 파싱/처리 실패:", e)
        # time.sleep(0.1)   # CPU 사용량 제어

def start_result_consumer():
    thread = threading.Thread(target=consume_result_topics, daemon=True)
    thread.start() 