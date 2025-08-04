# PenseurAI - AI 기반 브라우저 확장 프로그램

Chrome Extension (React 19 + Vite) + FastAPI 백엔드 + 마이크로서비스 아키텍처 기반의 실시간 AI 요약/추천 서비스.

## 개요

PenseurAI는 브라우저에서 YouTube 동영상 요약, PDF/문서 분석, 개인화된 콘텐츠 추천을 제공하는 AI 기반 Chrome 확장 프로그램입니다.

### 주요 기능
- **YouTube 동영상 요약**: 자막과 챕터를 분석하여 실시간 요약 제공
- **문서 분석**: PDF 파일의 텍스트 추출 및 요약(추천천)
- **실시간 스트리밍**: AI 처리 결과를 실시간으로 사용자에게 전달

## 기술 스택

### 프론트엔드
- **React 19**
- **Vite**: 빠른 빌드 도구
- **Chrome Extension Manifest V3**: 최신 확장 프로그램 표준
- **WebSocket**

### 백엔드
- **FastAPI**
- **SQLAlchemy**: ORM
- **MySQL**
- **JWT + Google OAuth**

### 마이크로서비스
- **gRPC**: 마이크로 서비스 간 고성능 통신
- **Protocol Buffers**: 타입 안전한 데이터 직렬화
- **Docker**

### AI 서비스
- **OpenAI GPT**: YouTube 요약
- **Perplexity API**: 추천
- **WatsonX**: 문서 요약 (LLAMA3)




### 1. 환경 변수 설정

#### 백엔드용 환경 변수 (`/project/.env`)
```bash
# AI 서비스 API 키
OPENAI_API_KEY=your_openai_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key
WATSONX_API_KEY=your_watsonx_api_key
WATSONX_PROJECT_ID=your_watsonx_project_id

# 데이터베이스
DATABASE_URL=mysql+pymysql://user:user_password@mysql:3306/penseur_db

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# JWT
JWT_SECRET_KEY=your_jwt_secret_key

# 확장 프로그램
EXTENSION_ID=your_extension_id
```

### 2. 개발 환경 실행

#### 프론트엔드 (Chrome Extension)
```bash
cd project/front
npm install
npm run dev
```

#### 백엔드 및 마이크로서비스
```bash
cd project
docker-compose up --build
```

### 3. Chrome Extension 설치

1. Chrome에서 `chrome://extensions/` 접속
2. "개발자 모드" 활성화
3. "압축해제된 확장 프로그램을 로드합니다" 클릭
4. `project/front/dist` 폴더 선택

## 📁 프로젝트 구조

```
project/
├── front/                    # Chrome Extension (React + Vite)
│   ├── src/
│   │   ├── components/      # React 컴포넌트
│   │   ├── utils/          # 유틸리티 함수
│   │   └── background.js   # Service Worker
│   └── public/             # 정적 파일
├── backend/                 # FastAPI 백엔드
│   ├── app/
│   │   ├── routers/        # API 라우터
│   │   ├── grpc_clients/   # gRPC 클라이언트
│   │   └── main.py         # FastAPI 앱
│   └── protos/             # Protocol Buffers 정의
├── llm-worker-youtube/      # YouTube 요약 서비스
├── llm-worker-docs/         # 문서 요약 서비스
├── llm-worker-rec/          # 추천 시스템 서비스
└── docker-compose.yml       # Docker Compose 설정
```


### API 문서
- FastAPI 자동 생성 문서: `http://localhost:8000/docs`
- ReDoc 문서: `http://localhost:8000/redoc`

### 디버깅
- Chrome DevTools: 확장 프로그램 디버깅
- Docker 로그: `docker-compose logs -f [service-name]`

### 테스트
```bash
# 프론트엔드 테스트
cd project/front
npm run lint

# 백엔드 테스트
cd project/backend
python -m pytest
```

## 배포

### 프로덕션 환경
1. 환경 변수 설정 (프로덕션 값으로)
2. 프론트엔드 빌드: `npm run build`
3. Docker 컨테이너 배포
4. Reverse Proxy 설정 (Nginx 권장)

### 환경별 설정
- **개발**: `docker-compose up --build`
- **스테이징**: 환경 변수 변경 후 동일한 명령어
- **프로덕션**: Docker Swarm 또는 Kubernetes 권장
