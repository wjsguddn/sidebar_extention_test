from fastapi import APIRouter, Request, Header, HTTPException
from pydantic import BaseModel
import json, os, jwt
import time

from ..grpc_clients.rec_client import RecClient
from ..websocket_manager import websocket_manager
from ..log_service import log_service
from ..models import ModeType

collect_browser_router = APIRouter()
rec_client = RecClient()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")


class CollectReq(BaseModel):
    url: str
    title: str
    text: str
    screenshot_base64: str = ""
    content_type: str = "default"
    content_period: str = "none"


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

    # 로그 시작
    request_id = log_service.start_request_log(user_id, ModeType.BROWSER)

    # 토큰 수 추정
    estimated_request_tokens = len(req.text.split()) + len(req.title.split()) + len(req.url.split())
    estimated_response_tokens = 0  # 스트림에서 누적

    first_token_received = False

    try:
        data = req.model_dump()
        
        # 설정값들 추출
        content_type = req.content_type
        content_period = req.content_period
        print(f"[COLLECT BROWSER] content_type={content_type}, content_period={content_period}")

        # gRPC Recommend stream 호출 및 WebSocket 전송
        async for chunk in rec_client.recommend_stream(user_id, json.dumps(data), content_type, content_period):
            print(chunk, flush=True)

            # 첫 토큰 수신 시 딜레이 기록
            if not first_token_received:
                print(f"[ROUTER] 첫 토큰 수신")
                log_service.first_token_received(request_id)
                first_token_received = True

            # 응답 토큰 수 누적
            estimated_response_tokens += len(chunk.content.split())

            await websocket_manager.send_to_user(user_id, {
                "type": "browser",
                "content": chunk.content,
                "is_final_b": chunk.is_final
            })

            # 스트림 종료 시점 기록
            if chunk.is_final:
                print(f"[ROUTER] 스트림 종료")
                log_service.stream_ended(request_id)

        print(f"[ROUTER] 로그 완료 호출: request_tokens={estimated_request_tokens}, response_tokens={estimated_response_tokens}")
        # 로그 완료 (성공)
        await log_service.complete_request_log(
            request_id=request_id,
            user_id=user_id,
            mode_type=ModeType.BROWSER,
            request_tokens=estimated_request_tokens,
            response_tokens=estimated_response_tokens,
        )

        return {"status": "ok"}

    except Exception as e:
        # 에러 발생 시에도 로그 완료
        if 'request_id' in locals():
            await log_service.complete_request_log(
                request_id=request_id,
                user_id=user_id,
                mode_type=ModeType.BROWSER,
                request_tokens=estimated_request_tokens,
                response_tokens=estimated_response_tokens,
            )
        raise HTTPException(status_code=500, detail=str(e))