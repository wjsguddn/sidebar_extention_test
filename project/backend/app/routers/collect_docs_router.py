from fastapi import APIRouter, Request, Header, HTTPException, UploadFile, File
from pydantic import BaseModel
import os, json
import requests as py_requests
import jwt

from ..grpc_clients.docs_client import DocsSummaryClient
from ..websocket_manager import websocket_manager

import re


collect_docs_router = APIRouter()
docs_client = DocsSummaryClient()
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

# PDF 추출 서비스 상태 확인 엔드포인트
@collect_docs_router.get("/health")
async def health_check():
    try:
        # PDF 추출 서비스 연결 테스트
        response = py_requests.get("http://host.docker.internal:5060/health", timeout=5)
        if response.status_code == 200:
            return {"status": "healthy", "pdf_service": "connected"}
        else:
            return {"status": "unhealthy", "pdf_service": "not responding"}
    except Exception as e:
        return {"status": "unhealthy", "pdf_service": "connection failed", "error": str(e)}


class CollectReq(BaseModel):
    filename: str
    text: str

def extract_clean_text(extracted_blocks: list[dict]) -> str:
    """텍스트 블록에서 요약에 적합한 형태로 텍스트 추출 및 정제"""

    IGNORE_SECTION_HEADERS = {"reference", "references", "참고문헌", "bibliography"}
    all_texts = []
    stop_extraction = False

    for block in extracted_blocks:
        block_type = block.get("type", "").lower()
        block_text = block.get("text", "").strip()

        if not block_text:
            continue

        # 참고 문헌 이후는 skip
        if block_type == "section header" and block_text.lower() in IGNORE_SECTION_HEADERS:
            stop_extraction = True
            continue

        if stop_extraction:
            continue

        # 문단 구분을 위해 빈 줄 삽입
        if block_type in {"section header"}:
            all_texts.append(f"\n{block_text}\n")
        elif block_type in {"text", "list item"}:
            all_texts.append(block_text)

    # 연속된 줄들 사이에 두 줄 간격 유지 (chunker 친화적)
    joined_text = "\n\n".join(all_texts).strip()
    return joined_text



def chunk_text(text, max_chars=1000, overlap=100):
    sentences = re.split(r'(?<=[.!?。])\s+', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # 누적한 chunk에 현재 문장을 추가해도 max_chars를 넘지 않으면 계속 누적
        if len(current_chunk) + len(sentence) <= max_chars:
            current_chunk += sentence + " "
        else:
            # 누적된 chunk를 저장
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
                # print(current_chunk.strip(), '\n\n\n')
            # 새로운 chunk 시작
            current_chunk = sentence + " "

    # 마지막 chunk는 길이에 상관없이 무조건 포함
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
        print(current_chunk.strip(), '\n\n\n')

    # Overlap 처리
    overlapped_chunks = []
    for i, chunk in enumerate(chunks):
        if i == 0:
            overlapped_chunks.append(chunk)
        else:
            prev_chunk_tail = chunks[i - 1][-overlap:] if len(chunks[i - 1]) >= overlap else chunks[i - 1]
            overlapped_chunks.append(prev_chunk_tail + " " + chunk)

    return overlapped_chunks


# PDF 업로드 → 추출 → chunk → gRPC 요약 → WebSocket 전송
@collect_docs_router.post("/collect/doc")
async def collect_docs(
    request: Request,
    file: UploadFile = File(...),
    authorization: str = Header(None)
):
    try:
        user_id = None
        # JWT 추출 및 decode
        if JWT_SECRET_KEY and authorization:
            if not authorization.startswith("Bearer "):
                print("401 Unauthorized: Authorization header missing or invalid")
                raise HTTPException(status_code=401, detail="Authorization header missing or invalid")
            token = authorization.split(" ")[1]
            try:
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
                user_id = payload.get("sub") or payload.get("user_id")
                if not user_id:
                    print("401 Unauthorized: user_id not found in token")
                    raise HTTPException(status_code=401, detail="user_id not found in token")
            except jwt.ExpiredSignatureError:
                print("401 Unauthorized: Token expired")
                raise HTTPException(status_code=401, detail="Token expired")
            except jwt.InvalidTokenError:
                print("401 Unauthorized: Invalid token")
                raise HTTPException(status_code=401, detail="Invalid token")
            except Exception as e:
                print(f"401 Unauthorized: JWT decode error: {e}")
                raise HTTPException(status_code=401, detail="Invalid token")

        # if not user_id:
        #     print("401 Unauthorized: user_id not found in token")
        #     raise HTTPException(status_code=401, detail="User not authenticated")
        # if not user_id:
        #     print("Warning: No user_id found, using default user")
        #     user_id = "anonymous"

        # PDF 파일 추출기 전송
        file_data = await file.read()

        multipart_form_data = {
            "file": (file.filename, file_data, file.content_type),
            "fast": (None, "true"),
        }

        # "http://localhost:5060" 대신 "http://host.docker.internal:5060/"넣음
        print(f'PDF 추출 서비스로 전송 시작: {file.filename}, 크기: {len(file_data)} bytes')
        try:
            response = py_requests.post("http://host.docker.internal:5060/", files=multipart_form_data, timeout=60)
            print('PDF 추출 서비스 응답 수신: ', response.status_code, '-------------------')
            print('응답 내용 길이:', len(response.content) if response.content else 0)
        except py_requests.exceptions.ConnectionError as e:
            print(f'PDF 추출 서비스 연결 실패: {e}')
            raise HTTPException(status_code=503, detail="PDF extraction service connection failed")
        except py_requests.exceptions.Timeout as e:
            print(f'PDF 추출 서비스 타임아웃: {e}')
            raise HTTPException(status_code=504, detail="PDF extraction service timeout")
        except Exception as e:
            print(f'PDF 추출 서비스 기타 오류: {e}')
            raise HTTPException(status_code=500, detail=f"PDF extraction service error: {str(e)}")

        if response.status_code != 200:
            print(f'PDF 추출 서비스 오류 응답: {response.status_code}, {response.text}')
            raise HTTPException(status_code=500, detail=f"Text extraction failed with status {response.status_code}")


        extracted_blocks = response.json()

        """
        file 객체 타입: <class 'starlette.datastructures.UploadFile'>

        file 객체: UploadFile(filename='document.pdf', size=3623117, headers=Headers({'content-disposition': 'form-data; name="file"; filename="document.pdf"', 'content-type': 'application/pdf'}))

        extracted_text 타입: <class 'list'>       

        발견된 type 종류: {'Page footer', 'Table', 'Caption', 'List item', 'Picture', 'Page header', 'Text', 'Section header'} 
        """

        if not isinstance(extracted_blocks, list) or len(extracted_blocks) == 0:
            raise HTTPException(status_code=500, detail="Invalid or empty extracted data")

        print('0---------------------')
        joined_text = extract_clean_text(extracted_blocks)

        chunks = chunk_text(joined_text)
        print('1---------------------', type(chunks), len(chunks) if chunks else 'None')

        # gRPC stream 호출 → WebSocket으로 실시간 전송
        async for chunk in docs_client.docssummary_stream(chunks, user_id):
            print('gRPC chunk:', chunk)
            await websocket_manager.send_to_user(user_id, {
                "type": "summary_chunk",
                "content": chunk
            })
        print('2---------------------')
        await websocket_manager.send_to_user(user_id, {
            "type": "summary_complete",
            "filename": file.filename
        })
        print('3---------------------')

        return {"status": "ok"}

    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid JWT token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# 예시: /ws/summary/{user_id} WebSocket 연결

# 1. 클라이언트에서 WebSocket 연결
# 2. 서버에서는 해당 user_id로 gRPC stream을 열고
# 3. 받은 chunk/token을 WebSocket으로 바로 전송