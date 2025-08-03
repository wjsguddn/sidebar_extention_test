# 추천 시스템 (llm-worker-rec)

사용자의 브라우징 패턴을 분석하여 개인화된 콘텐츠 추천을 제공하는 gRPC 마이크로서비스입니다.

## 주요 기능

### 개인화 추천
- **브라우징 패턴 분석**: 사용자의 웹 서핑 행동 분석
- **콘텐츠 유형 분류**: 관심사별 콘텐츠 카테고리화
- **실시간 추천**: 사용자 행동 변화에 따른 동적 추천

### AI 기반
- **OpenAI GPT**: 고품질 추천 콘텐츠 생성
- **Perplexity API**: 보조 AI 서비스 활용
- **맥락 이해**: 사용자 상황에 맞는 맞춤형 추천

### gRPC
- **스트리밍 응답**: 실시간 추천 결과 전달
- **타입 안전성**: Protocol Buffers 기반
- **고성능**: HTTP/2 기반 통신

## 서비스 구조

### gRPC 프로토콜 정의
```protobuf
// protos/recommendation.proto
syntax = "proto3";

package recommendation;

message RecommendRequest {
  string user_id = 1;
  string browser_context = 2;  // 브라우저 수집 정보 (JSON)
  string content_type = 3;     // 추천 컨텐츠 유형
  string content_period = 4;   // 컨텐츠 기간 필터
}

message RecommendResponse {
  string content = 1;      // 추천 결과 (스트림 chunk)
  string is_final = 2;     // 마지막 chunk 여부
}

service RecommendationService {
  rpc Recommend (RecommendRequest) returns (stream RecommendResponse);
}
```

### 주요 함수들

#### 1. 브라우징 데이터 분석
```python
def analyze_browsing_pattern(browser_context: dict) -> dict:
    """브라우징 패턴 분석"""
    analysis = {
        "topics": extract_topics(browser_context),
        "interests": analyze_interests(browser_context),
        "behavior_pattern": analyze_behavior(browser_context),
        "content_preferences": extract_preferences(browser_context)
    }
    return analysis
```

#### 2. 관심사 추출
```python
def extract_topics(browser_context: dict) -> List[str]:
    """방문한 웹사이트에서 관심사 추출"""
    topics = []
    
    for site in browser_context.get("visited_sites", []):
        url = site.get("url", "")
        title = site.get("title", "")
        
        # URL과 제목에서 키워드 추출
        keywords = extract_keywords(url, title)
        topics.extend(keywords)
    
    # 중복 제거 및 빈도 분석
    return get_top_topics(topics, limit=10)
```

#### 3. AI 추천 생성
```python
async def generate_recommendations(user_id: str, analysis: dict, content_type: str = "general") -> str:
    """AI를 사용한 개인화 추천 생성"""
    prompt = f"""
    다음은 사용자의 브라우징 패턴 분석 결과입니다:
    
    사용자 ID: {user_id}
    관심사: {analysis['topics']}
    행동 패턴: {analysis['behavior_pattern']}
    콘텐츠 선호도: {analysis['content_preferences']}
    요청 유형: {content_type}
    
    이 정보를 바탕으로 사용자에게 유용한 콘텐츠를 추천해 주세요.
    추천은 구체적이고 실용적이어야 하며, 사용자의 관심사와 일치해야 합니다.
    """
    
    response = await call_openai_api(prompt)
    return response
```

#### 4. OpenAI API 호출
```python
async def call_openai_api(prompt: str) -> str:
    """OpenAI API 호출"""
    import openai
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "당신은 사용자의 관심사와 행동 패턴을 분석하여 개인화된 콘텐츠를 추천하는 전문가입니다."},
            {"role": "user", "content": prompt}
        ],
        stream=True,
        max_tokens=500,
        temperature=0.7
    )
    
    return response
```

## 데이터 흐름

### 1. 추천 생성 파이프라인
```
브라우징 데이터 → 패턴 분석 → AI 추천 생성 → 실시간 전송
```

### 2. 사용자 행동 분석
```
방문 사이트 → 관심사 추출 → 선호도 분석 → 추천 알고리즘
```

### 3. 실시간 통신
```
FastAPI → gRPC 스트리밍 → OpenAI API → WebSocket → 클라이언트
```

## 환경 설정

### 환경 변수
```bash
# AI 서비스 API 키
OPENAI_API_KEY=your_openai_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key

# gRPC 서버 설정
GRPC_PORT=50051
```

### 의존성 설치
```bash
pip install -r requirements.txt
```

### 서비스 실행
```bash
# Docker Compose로 실행
docker-compose up llm-worker-rec

# 또는 직접 실행
python main.py
```

## 프로젝트 구조

```
llm-worker-rec/
├── main.py                 # gRPC 서버 메인 파일
├── requirements.txt        # Python 의존성
├── Dockerfile             # Docker 이미지 정의
├── protos/                # Protocol Buffers 정의
│   └── recommendation.proto
└── README.md              # 이 파일
```

## 🔄 gRPC 서비스 구현

### 서비스 클래스
```python
class RecommendationService(recommendation_pb2_grpc.RecommendationServiceServicer):
    async def Recommend(self, request, context):
        """추천 gRPC 스트리밍 서비스"""
        try:
            # 1. 요청 데이터 파싱
            browser_context = json.loads(request.browser_context)
            user_id = request.user_id
            content_type = request.content_type
            content_period = request.content_period
            
            # 2. 브라우징 패턴 분석
            analysis = analyze_browsing_pattern(browser_context)
            
            # 3. AI 추천 생성 및 스트리밍
            async for chunk in generate_recommendations(user_id, analysis, content_type):
                yield recommendation_pb2.RecommendResponse(
                    content=chunk,
                    is_final="false"
                )
            
            # 4. 최종 응답
            yield recommendation_pb2.RecommendResponse(
                content="추천 완료",
                is_final="true"
            )
            
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"추천 처리 중 오류: {str(e)}")
```

### 서버 실행
```python
async def serve():
    """gRPC 서버 실행"""
    server = grpc.aio.server()
    recommendation_pb2_grpc.add_RecommendationServiceServicer_to_server(
        RecommendationService(), server
    )
    
    listen_addr = f'[::]:{os.getenv("GRPC_PORT", "50051")}'
    server.add_insecure_port(listen_addr)
    
    await server.start()
    await server.wait_for_termination()
```

## 성능 최적화

### 1. 캐싱 전략
```python
# 사용자 분석 결과 캐싱
import asyncio
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_analyze_browsing_pattern(browser_context_hash: str) -> dict:
    """브라우징 패턴 분석 결과 캐싱"""
    return analyze_browsing_pattern(browser_context_hash)
```

### 2. 비동기 처리
```python
# 여러 분석 작업을 동시에 실행
async def parallel_analysis(browser_context: dict) -> dict:
    """병렬 분석 처리"""
    tasks = [
        analyze_topics(browser_context),
        analyze_interests(browser_context),
        analyze_behavior(browser_context)
    ]
    
    results = await asyncio.gather(*tasks)
    return {
        "topics": results[0],
        "interests": results[1],
        "behavior": results[2]
    }
```

### 3. 스트리밍 응답
```python
# 실시간으로 추천 결과 전달
async for chunk in ai_response:
    yield RecommendResponse(content=chunk, is_final="false")
```

## 디버깅

### 로그 확인
```bash
# Docker 로그
docker-compose logs -f llm-worker-rec

# 직접 실행 시
python main.py --debug
```

### gRPC 테스트
```python
# gRPC 클라이언트 테스트
import grpc
import recommendation_pb2
import recommendation_pb2_grpc

async def test_recommendation():
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = recommendation_pb2_grpc.RecommendationServiceStub(channel)
        
        browser_context = {
            "visited_sites": [
                {"url": "https://github.com", "title": "GitHub"},
                {"url": "https://stackoverflow.com", "title": "Stack Overflow"}
            ],
            "search_queries": ["python tutorial", "machine learning"],
            "time_spent": {"github.com": 1200, "stackoverflow.com": 800}
        }
        
        request = recommendation_pb2.RecommendRequest(
            user_id="test_user",
            browser_context=json.dumps(browser_context),
            content_type="technical",
            content_period="recent"
        )
        
        async for response in stub.Recommend(request):
            print(f"추천: {response.content}")
```

## 모니터링

### 성능 메트릭
- **처리 시간**: 추천 생성 소요 시간
- **사용자 만족도**: 추천 클릭률
- **성공률**: 추천 생성 성공 비율
- **에러율**: API 호출 실패 비율

### 로그 분석
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 처리 과정 로깅
logger.info(f"추천 시작: 사용자 {user_id}")
logger.info(f"분석된 관심사: {len(topics)}개")
logger.info(f"추천 생성 완료: {len(recommendation)} 문자")
```

## 보안 고려사항

### 개인정보 보호
- **데이터 익명화**: 사용자 식별 정보 제거
- **암호화**: 민감한 브라우징 데이터 암호화
- **접근 제어**: API 키 기반 인증

### 입력 검증
```python
def validate_browser_context(browser_context: dict) -> bool:
    """브라우저 컨텍스트 유효성 검증"""
    required_fields = ["visited_sites", "search_queries"]
    
    for field in required_fields:
        if field not in browser_context:
            return False
    
    # 데이터 크기 제한
    if len(str(browser_context)) > 10000:
        return False
    
    return True
```

### 에러 처리
```python
try:
    # 브라우징 데이터 분석
    analysis = analyze_browsing_pattern(browser_context)
    if not analysis:
        raise ValueError("분석 결과가 비어있습니다")
except Exception as e:
    # 적절한 에러 응답
    context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
```
