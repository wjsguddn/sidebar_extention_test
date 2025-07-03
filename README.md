# Sidebar Extension Project

브라우저 확장 프로그램(React + Vite) + FastAPI 백엔드 + LLM 워커(Python, Kafka) 기반의 실시간 추천/요약 서비스.

---

## 1. 환경 변수 설정

### 1-1. `/project/.env` (백엔드/워커용)

```
KAFKA_BOOTSTRAP=kafka:9092

OPENAI_API_KEY=your_openai_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key

DATABASE_URL=mysql+pymysql://user:user_password@mysql:3306/penseur_db

GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

EXTENSION_ID=your_extension_id

JWT_SECRET_KEY=your_jwt_secret
```

### 1-2. `/project/front/.env` (프론트엔드용)

- **개발용(.env.local)**
  ```
  VITE_API_BASE=http://localhost:8000
  VITE_GOOGLE_CLIENT_ID=your_google_client_id
  ```
- **배포용**
  ```
  VITE_API_BASE=https://your-production-backend-url
  VITE_GOOGLE_CLIENT_ID=your_google_client_id
  ```

※ `.env.local` 대신 `.env`도 무관.  
※ API 주소는 실제 백엔드 주소와 일치해야 함.

---

## 2. 실행

### 2-1. 프론트(React)

```bash
cd project/front
npm install
npm run dev         # 개발 서버 실행
# 또는
npm run build       # 배포용 빌드(dist 폴더 생성)
```

### 2-2. 백엔드/LLM 워커/Kafka (Docker Compose)

1. ```bash
   cd project
   ```
2. **Docker Desktop 실행**  
   윈도우/맥은 Docker Desktop 실행, 리눅스는 Docker 데몬만 실행되어 있으면 됨


3. **컨테이너 실행**
   ```bash
   docker-compose up --build
   ```
   - FastAPI, llm-worker, Kafka, Zookeeper 등 모든 서비스 컨테이너 실행.

---

## 3. 기타 참고사항

- **Kafka, Zookeeper 등**은 `docker-compose.yml`로 자동 실행.
- **프론트엔드와 백엔드의 API 주소**(`VITE_API_BASE`)가 일치해야 정상 동작.
- **배포 시**:  
  - 프론트엔드 빌드 결과(`/dist`)를 서비스 서버에 배포  
  - 백엔드/워커는 서버 환경에 맞게 Docker로 실행
