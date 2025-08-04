# 문서 요약 서비스 (llm-worker-docs)

PDF, DOC, DOCX 파일의 텍스트를 추출하고 AI 기반 요약을 제공하는 gRPC 마이크로서비스

## 주요 기능

### 문서 처리
- **PDF 텍스트 추출**: 레이아웃 분석을 통한 정확한 텍스트 추출
- **DOC/DOCX 지원**: Microsoft Office 문서 처리
- **다국어 지원**: 한국어, 영어 문서 처리

### AI 요약
- **WatsonX API**: IBM의 고성능 AI 모델 활용
- **Perplexity API**: 보조 AI 서비스
- **2단계 요약**: 청크별 미니 요약 → 전체 최종 요약

### gRPC
- **스트리밍 응답**: 실시간 요약 진행 상황 전달
- **타입 안전성**: Protocol Buffers 기반
- **고성능**: HTTP/2 기반 통신

## 서비스 구조

### gRPC 프로토콜 정의
```protobuf
// protos/docssummary.proto
syntax = "proto3";

package docssummary;

message DocsSummaryRequest {
  string user_id = 1;
  string chunk = 2;  // 문서 청크
}

message DocsSummaryResponse {
  string content = 1;      // 요약 내용
  string is_final = 2;     // 최종 응답 여부
}

service DocsSummaryService {
  rpc SummarizeStream (stream DocsSummaryRequest) returns (stream DocsSummaryResponse);
}
```

### 주요 함수들

#### 1. 문서 청크 처리
```python
async def process_document_chunks(chunks: List[str]) -> List[str]:
    """문서 청크들을 처리하여 요약 생성"""
    mini_summaries = []
    
    for chunk in chunks:
        # 각 청크별 미니 요약 생성
        mini_summary = await generate_mini_summary(chunk)
        mini_summaries.append(mini_summary)
        
        # 실시간으로 미니 요약 전송
        yield DocsSummaryResponse(
            content=mini_summary,
            is_final="false"
        )
    
    # 전체 최종 요약 생성
    final_summary = await generate_final_summary(mini_summaries)
    yield DocsSummaryResponse(
        content=final_summary,
        is_final="true"
    )
```

#### 2. 미니 요약 생성
```python
async def generate_mini_summary(chunk: str) -> str:
    """청크별 미니 요약 생성"""
    prompt = f"""
    다음 문서 청크를 간결하게 요약해 주세요:
    
    {chunk}
    
    요약:
    """
    
    response = await call_watsonx_api(prompt)
    return response
```

#### 3. 최종 요약 생성
```python
async def generate_final_summary(mini_summaries: List[str]) -> str:
    """전체 미니 요약을 종합한 최종 요약 생성"""
    combined_summaries = "\n\n".join(mini_summaries)
    
    prompt = f"""
    다음은 문서의 각 부분별 요약입니다. 이를 종합하여 전체 문서의 핵심 내용을 요약해 주세요:
    
    {combined_summaries}
    
    전체 문서 요약:
    """
    
    response = await call_watsonx_api(prompt)
    return response
```

#### 4. WatsonX API 호출
```python
async def call_watsonx_api(prompt: str) -> str:
    """WatsonX API 호출"""
    import requests
    
    payload = {
        "model_id": "meta-llama/llama-3-70b-instruct",
        "input": prompt,
        "parameters": {
            "max_new_tokens": 256,
            "temperature": 0.7,
            "top_p": 0.9
        }
    }
    
    headers = {
        "Authorization": f"Bearer {os.getenv('WATSONX_API_KEY')}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        "https://us-south.ml.cloud.ibm.com/v1/watsonx/generate",
        json=payload,
        headers=headers
    )
    
    return response.json()["results"][0]["generated_text"]
```

## 데이터 흐름

### 1. 문서 처리 파이프라인
```
PDF/DOC 파일 → 텍스트 추출기 → 청크 분할 → AI 요약 → 실시간 전송
```

### 2. 요약 생성 과정
```
문서 청크 → 미니 요약 (각 청크별) → 최종 요약 (전체 종합)
```

### 3. 실시간 통신
```
FastAPI → gRPC 스트리밍 → WatsonX API → WebSocket → 클라이언트
```

## 환경 설정

### 환경 변수
```bash
# AI 서비스 API 키
WATSONX_API_KEY=your_watsonx_api_key
WATSONX_PROJECT_ID=your_watsonx_project_id
PERPLEXITY_API_KEY=your_perplexity_api_key

# gRPC 서버 설정
GRPC_PORT=50053
```

### 의존성 설치
```bash
pip install -r requirements.txt
```

### 서비스 실행
```bash
# Docker Compose로 실행
docker-compose up llm-worker-docs

# 또는 직접 실행
python main.py
```

## 프로젝트 구조

```
llm-worker-docs/
├── main.py                 # gRPC 서버 메인 파일
├── requirements.txt        # Python 의존성
├── Dockerfile             # Docker 이미지 정의
├── protos/                # Protocol Buffers 정의
│   └── docssummary.proto
└── README.md              # 이 파일
```

## gRPC 서비스 구현

### 서비스 클래스
```python
class DocsSummaryService(docssummary_pb2_grpc.DocsSummaryServiceServicer):
    async def SummarizeStream(self, request_iterator, context):
        """문서 요약 gRPC 스트리밍 서비스"""
        try:
            chunks = []
            
            # 1. 요청 스트림에서 청크 수집
            async for request in request_iterator:
                chunks.append(request.chunk)
            
            # 2. 각 청크별 미니 요약 생성 및 스트리밍
            mini_summaries = []
            for chunk in chunks:
                mini_summary = await generate_mini_summary(chunk)
                mini_summaries.append(mini_summary)
                
                yield docssummary_pb2.DocsSummaryResponse(
                    content=mini_summary,
                    is_final="false"
                )
            
            # 3. 최종 요약 생성 및 전송
            final_summary = await generate_final_summary(mini_summaries)
            yield docssummary_pb2.DocsSummaryResponse(
                content=final_summary,
                is_final="true"
            )
            
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"요약 처리 중 오류: {str(e)}")
```

### 서버 실행
```python
async def serve():
    """gRPC 서버 실행"""
    server = grpc.aio.server()
    docssummary_pb2_grpc.add_DocsSummaryServiceServicer_to_server(
        DocsSummaryService(), server
    )
    
    listen_addr = f'[::]:{os.getenv("GRPC_PORT", "50053")}'
    server.add_insecure_port(listen_addr)
    
    await server.start()
    await server.wait_for_termination()
```

## 성능 최적화

### 1. 청크 기반 처리
```python
# 대용량 문서를 청크로 분할하여 처리
def split_document_into_chunks(text: str, chunk_size: int = 2000) -> List[str]:
    """문서를 청크로 분할"""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size):
        chunk = ' '.join(words[i:i + chunk_size])
        chunks.append(chunk)
    
    return chunks
```

### 2. 병렬 처리
```python
# 여러 청크를 동시에 처리
async def process_chunks_parallel(chunks: List[str]) -> List[str]:
    """청크들을 병렬로 처리"""
    tasks = [generate_mini_summary(chunk) for chunk in chunks]
    results = await asyncio.gather(*tasks)
    return results
```

### 3. 스트리밍 응답
```python
# 실시간으로 처리 결과 전달
async for chunk in chunks:
    summary = await generate_mini_summary(chunk)
    yield DocsSummaryResponse(content=summary, is_final="false")
```

## 디버깅

### 로그 확인
```bash
# Docker 로그
docker-compose logs -f llm-worker-docs

# 직접 실행 시
python main.py --debug
```

### gRPC 테스트
```python
# gRPC 클라이언트 테스트
import grpc
import docssummary_pb2
import docssummary_pb2_grpc

async def test_docs_summary():
    async with grpc.aio.insecure_channel('localhost:50053') as channel:
        stub = docssummary_pb2_grpc.DocsSummaryServiceStub(channel)
        
        # 요청 스트림 생성
        async def request_generator():
            chunks = ["첫 번째 청크", "두 번째 청크", "세 번째 청크"]
            for chunk in chunks:
                yield docssummary_pb2.DocsSummaryRequest(
                    user_id="test_user",
                    chunk=chunk
                )
        
        # 응답 스트림 처리
        async for response in stub.SummarizeStream(request_generator()):
            print(f"응답: {response.content}")
            if response.is_final == "true":
                print("최종 요약 완료")
```

## 모니터링

### 성능 메트릭
- **처리 시간**: 문서 요약 생성 소요 시간
- **청크 수**: 처리된 문서 청크 수
- **성공률**: 요약 생성 성공 비율
- **에러율**: API 호출 실패 비율

### 로그 분석
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 처리 과정 로깅
logger.info(f"문서 요약 시작: {len(chunks)} 청크")
logger.info(f"청크 {i+1}/{len(chunks)} 처리 중")
logger.info(f"미니 요약 완료: {len(mini_summary)} 문자")
logger.info(f"최종 요약 완료: {len(final_summary)} 문자")
```

## 보안 고려사항

### API 키 관리
- 환경 변수를 통한 API 키 관리
- Docker Secrets 활용 (프로덕션)
- 키 로테이션 정책

### 입력 검증
```python
def validate_document_chunk(chunk: str) -> bool:
    """문서 청크 유효성 검증"""
    if not chunk or len(chunk.strip()) == 0:
        return False
    if len(chunk) > 10000:  # 최대 길이 제한
        return False
    return True
```

### 에러 처리
```python
try:
    # WatsonX API 호출
    response = await call_watsonx_api(prompt)
    if not response:
        raise ValueError("API 응답이 비어있습니다")
except Exception as e:
    # 적절한 에러 응답
    context.abort(grpc.StatusCode.INTERNAL, str(e))
```