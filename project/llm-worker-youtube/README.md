# YouTube 요약 서비스 (llm-worker-youtube)

YouTube 동영상의 자막과 챕터를 분석하여 AI 기반 실시간 요약을 제공하는 gRPC 마이크로서비스

## 주요 기능

### YouTube 동영상 분석
- **자막 추출**: YouTube 자동 생성 자막 및 수동 자막 지원
- **챕터 분석**: 동영상 챕터 정보 추출 및 활용
- **다국어 지원**: 한국어, 영어 자막 처리

### AI 요약
- **OpenAI GPT**: 고품질 요약 생성
- **Perplexity API**: 보조 AI 서비스 활용
- **실시간 스트리밍**: 처리 과정을 실시간으로 전달

### gRPC
- **스트리밍 응답**: 긴 처리 시간을 실시간으로 전달
- **타입 안전성**: Protocol Buffers 기반
- **고성능**: HTTP/2 기반 통신

## 서비스 구조

### gRPC 프로토콜 정의
```protobuf
// protos/youtubesummary.proto
syntax = "proto3";

package youtubesummary;

message YoutubeSummaryRequest {
  string user_id = 1;
  string youtube_context = 2;  // JSON 문자열
}

message YoutubeSummaryResponse {
  string content = 1;      // 요약 내용
  string is_final = 2;     // 최종 응답 여부
}

service YoutubeSummaryService {
  rpc YoutubeSummary (YoutubeSummaryRequest) returns (stream YoutubeSummaryResponse);
}
```

### 주요 함수들

#### 1. YouTube URL 파싱
```python
def extract_video_id(youtube_url: str) -> str:
    """YouTube URL에서 video ID를 추출"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/v\/([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)'
    ]
    # 다양한 YouTube URL 패턴 지원
```

#### 2. 자막 추출
```python
def get_transcript_text(video_id: str, languages=['ko', 'en']) -> str:
    """자막 가져오고 텍스트로 변환"""
    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
    text = "\n".join(
        f"{format_seconds(line['start'])} {line['text']}"
        for line in transcript
    )
    return text
```

#### 3. 챕터 정보 추출
```python
def get_chapter(url):
    """YouTube 동영상 챕터 정보 추출"""
    with yt_dlp.YoutubeDL({}) as ydl:
        info = ydl.extract_info(url, download=False)
        chapters = "\n".join(
            f"{format_seconds(line['start_time'])} {line['title']}"
            for line in info.get('chapters', [])
        )
        return chapters
```

#### 4. AI 요약 생성
```python
async def generate_youtube_summary(transcript: str, video_title: str = "", chapters: str = "") -> str:
    """OpenAI API를 사용한 YouTube 요약 생성"""
    prompt = f"""
    다음은 YouTube 동영상의 제목과 챕터, 자막정보 입니다.
    자막은 유튜브 자동 생성으로, 반복되거나 의미 없는 단어·잡음이 포함되어 있을 수 있습니다.
    문맥을 추론해 주요 내용 중심으로 요약해 주세요.
    
    [동영상 제목]: {video_title}
    [챕터 정보]: {chapters}
    [자막 내용]: {transcript}
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        stream=True
    )
    
    return response
```

## 데이터 흐름

### 1. 요청 처리
```
FastAPI → gRPC 요청 → YoutubeSummaryService
```

### 2. 데이터 추출
```
YouTube URL → Video ID → 자막 + 챕터 정보
```

### 3. AI 처리
```
추출된 데이터 → OpenAI API → 요약 생성
```

### 4. 응답 전송
```
생성된 요약 → gRPC 스트리밍 → FastAPI → WebSocket → 클라이언트
```

## 환경 설정

### 환경 변수
```bash
# AI 서비스 API 키
OPENAI_API_KEY=your_openai_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key

# gRPC 서버 설정
GRPC_PORT=50052
```

### 의존성 설치
```bash
pip install -r requirements.txt
```

### 서비스 실행
```bash
# Docker Compose로 실행
docker-compose up llm-worker-youtube

# 또는 직접 실행
python main.py
```

## 프로젝트 구조

```
llm-worker-youtube/
├── main.py                 # gRPC 서버 메인 파일
├── requirements.txt        # Python 의존성
├── Dockerfile             # Docker 이미지 정의
├── protos/                # Protocol Buffers 정의
│   └── youtubesummary.proto
└── README.md              # 이 파일
```

## gRPC 서비스 구현

### 서비스 클래스
```python
class YoutubeSummaryService(youtubesummary_pb2_grpc.YoutubeSummaryServiceServicer):
    async def YoutubeSummary(self, request, context):
        """YouTube 요약 gRPC 서비스"""
        try:
            # 1. 요청 데이터 파싱
            data = json.loads(request.youtube_context)
            youtube_url = data.get('youtube_url')
            video_title = data.get('title', '')
            
            # 2. YouTube 데이터 추출
            video_id = extract_video_id(youtube_url)
            transcript = get_transcript_text(video_id)
            chapters = get_chapter(youtube_url)
            
            # 3. AI 요약 생성 및 스트리밍
            async for chunk in generate_youtube_summary(transcript, video_title, chapters):
                yield youtubesummary_pb2.YoutubeSummaryResponse(
                    content=chunk,
                    is_final="false"
                )
            
            # 4. 최종 응답
            yield youtubesummary_pb2.YoutubeSummaryResponse(
                content="요약 완료",
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
    youtubesummary_pb2_grpc.add_YoutubeSummaryServiceServicer_to_server(
        YoutubeSummaryService(), server
    )
    
    listen_addr = f'[::]:{os.getenv("GRPC_PORT", "50052")}'
    server.add_insecure_port(listen_addr)
    
    await server.start()
    await server.wait_for_termination()
```

## 성능 최적화

### 1. 비동기 처리
```python
# asyncio를 활용한 비동기 처리
async def process_youtube_data(url: str):
    # 여러 작업을 동시에 실행
    transcript_task = get_transcript_async(video_id)
    chapter_task = get_chapter_async(url)
    
    transcript, chapters = await asyncio.gather(transcript_task, chapter_task)
```

### 2. 스트리밍 응답
```python
# 실시간으로 처리 결과 전달
async for chunk in ai_response:
    yield YoutubeSummaryResponse(content=chunk, is_final="false")
```

### 3. 에러 처리
```python
try:
    # YouTube 데이터 추출
    transcript = get_transcript_text(video_id)
    if not transcript:
        raise ValueError("자막을 찾을 수 없습니다")
except Exception as e:
    # 적절한 에러 응답
    context.abort(grpc.StatusCode.NOT_FOUND, str(e))
```

## 디버깅

### 로그 확인
```bash
# Docker 로그
docker-compose logs -f llm-worker-youtube

# 직접 실행 시
python main.py --debug
```

### gRPC 테스트
```python
# gRPC 클라이언트 테스트
import grpc
import youtubesummary_pb2
import youtubesummary_pb2_grpc

async def test_youtube_summary():
    async with grpc.aio.insecure_channel('localhost:50052') as channel:
        stub = youtubesummary_pb2_grpc.YoutubeSummaryServiceStub(channel)
        request = youtubesummary_pb2.YoutubeSummaryRequest(
            user_id="test_user",
            youtube_context='{"youtube_url": "https://youtube.com/watch?v=...", "title": "테스트"}'
        )
        
        async for response in stub.YoutubeSummary(request):
            print(f"응답: {response.content}")
```

## 모니터링

### 성능 메트릭
- **처리 시간**: YouTube 요약 생성 소요 시간
- **성공률**: 요약 생성 성공 비율
- **에러율**: API 호출 실패 비율

### 로그 분석
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 처리 과정 로깅
logger.info(f"YouTube 요약 시작: {video_id}")
logger.info(f"자막 길이: {len(transcript)} 문자")
logger.info(f"요약 완료: {len(summary)} 문자")
```

## 보안 고려사항

### API 키 관리
- 환경 변수를 통한 API 키 관리
- Docker Secrets 활용 (프로덕션)
- 키 로테이션 정책

### 입력 검증
```python
def validate_youtube_url(url: str) -> bool:
    """YouTube URL 유효성 검증"""
    patterns = [
        r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^https?://youtu\.be/[\w-]+'
    ]
    return any(re.match(pattern, url) for pattern in patterns)
```