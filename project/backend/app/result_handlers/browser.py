import asyncio
from ..websocket_manager import websocket_manager

async def send_to_front(user_id: str, front_result: dict):
    await websocket_manager.send_to_user(user_id, front_result)

def handle_browser_result(result: dict):
    print(f"[result.browser] result={result}")
    user_id = result.get("user_id")
    front_result = {
        "summary": result.get("summary"),
        "recommendations": result.get("recommendations")
    }

    if not user_id:
        print("user_id가 없는 result, 프론트로 전송 불가")
        return
    # 비동기 함수 실행 (동기 컨슈머에서 호출 시)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop = asyncio.get_event_loop()
    loop.run_until_complete(send_to_front(user_id, front_result))