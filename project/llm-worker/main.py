from confluent_kafka import KafkaException, Consumer
import os, json, time


BOOT = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
consumer = Consumer({
    "bootstrap.servers": BOOT,
    "group.id": "llm-worker",
    "auto.offset.reset": "earliest",
    "session.timeout.ms": 6000
})
consumer.subscribe(["browser.events"])

print("LLM 워커 대기중…")

while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    if msg.error():
        print("Kafka error:", msg.error())
        continue
    try:
        data = json.loads(msg.value().decode())
    except Exception as e:
        print("JSON decode 실패:", e, "| RAW:", msg.value())
        continue

    print("메시지 수신:")
    print("  URL:", data.get("url", ""))
    print("  Title:", data.get("title", ""))
    screenshot = data.get("screenshot_base64", "")
    print("  Screenshot:", screenshot[:50] + ("..." if len(screenshot) > 60 else ""))
    text = data.get("text", "")
    print("  Text:")
    # print(text)     # 텍스트 전체 출력
    text_lines = text.splitlines()
    for line in text_lines[:50]:    # llm-worker 로그에 출력할 text 줄수
        print("   ", line)
    time.sleep(2)
    print("추천 완료 (dummy)\n")
