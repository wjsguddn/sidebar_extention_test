# PenseurAI Chrome Extension

React 19 + Vite 기반의 AI 브라우저 확장 프로그램. YouTube 동영상 요약, 문서 분석, 개인화된 추천 제공.

## 주요 기능

### YouTube 동영상 요약
- YouTube 동영상 자막 및 챕터 자동 분석
- AI 기반 실시간 요약 생성
- 스트리밍 방식으로 진행 상황 표시

### 문서 분석
- PDF, DOC, DOCX 파일 자동 감지
- 텍스트 추출 및 AI 요약
- 문서 레이아웃 분석

### 개인화 추천
- 브라우징 패턴 분석
- 맞춤형 콘텐츠 추천
- 실시간 추천 결과 제공

### 실시간 통신
- WebSocket을 통한 실시간 데이터 스트리밍
- 자동 새로고침 기능
- 다크/라이트 테마 지원

## 기술 스택

### 핵심 기술
- **React 19**: 최신 React 버전
- **Vite**: 빠른 빌드 도구
- **Chrome Extension Manifest V3**: 최신 확장 프로그램 표준

### 개발 도구
- **ESLint**: 코드 품질 관리
- **CRXJS Vite Plugin**: Chrome Extension 빌드
- **WebSocket**: 실시간 통신


## 개발 환경 설정

### 1. 의존성 설치
```bash
npm install
```

### 2. 개발 서버 실행
```bash
npm run dev
```

### 3. 프로덕션 빌드
```bash
npm run build
```

### 4. 코드 검사
```bash
npm run lint
```

## 프로젝트 구조

```
src/
├── components/
│   ├── pages/              # 페이지 컴포넌트
│   │   ├── DefaultPage.jsx
│   │   ├── YoutubeSummary.jsx
│   │   ├── DocumentSummary.jsx
│   │   ├── Recommendation.jsx
│   │   ├── LoginPage.jsx
│   │   └── SensitivePage.jsx
│   └── ui/                 # UI 컴포넌트
│       ├── Header.jsx
│       ├── Footer.jsx
│       ├── Card.jsx
│       ├── Button.jsx
│       ├── LoadingSpinner.jsx
│       └── UserProfile.jsx
├── utils/                  # 유틸리티 함수
│   ├── jwtUtils.js         # JWT 토큰 관리
│   ├── websocketProvider.jsx # WebSocket 연결
│   ├── pageMode.js         # 페이지 모드 감지
│   ├── constants.js         # 상수 정의
│   ├── browserCollector.js # 브라우저 데이터 수집
│   └── documentCollector.js # 문서 데이터 수집
├── styles/                 # 스타일 파일
│   └── colors.css          # 색상 변수
├── assets/                 # 정적 자산
├── App.jsx                 # 메인 앱 컴포넌트
├── main.jsx               # 앱 진입점
├── background.js           # Service Worker
└── contentReady.js         # Content Script
```

## 주요 컴포넌트

### App.jsx
메인 애플리케이션 컴포넌트로 다음 기능을 담당합니다:
- 페이지 모드 감지 및 라우팅
- 사용자 인증 상태 관리
- 테마 관리 (다크/라이트)
- 자동 새로고침 설정

### 페이지 컴포넌트들
- **DefaultPage**: 기본 페이지 (로그인 전)
- **LoginPage**: Google OAuth 로그인
- **YoutubeSummary**: YouTube 동영상 요약 표시
- **DocumentSummary**: 문서 분석 결과 표시
- **Recommendation**: 개인화 추천 결과 표시
- **SensitivePage**: 민감한 콘텐츠 경고

### UI 컴포넌트들
- **Header**: 상단 네비게이션
- **Footer**: 하단 정보 표시
- **Card**: 콘텐츠 카드 컴포넌트
- **LoadingSpinner**: 로딩 표시
- **UserProfile**: 사용자 프로필

## 상태 관리

### 로컬 상태
```javascript
// Chrome Storage API 사용
chrome.storage.local.set({ autoRefreshEnabled: true });
chrome.storage.local.get(['token'], (result) => {
  // 토큰 관리
});
```

### 실시간 통신
```javascript
// WebSocket 연결
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
  // 실시간 데이터 처리
};
```

## 테마 시스템

### 다크/라이트 테마
```css
/* CSS Variables 사용 */
:root {
  --primary-color: #007bff;
  --background-color: #ffffff;
  --text-color: #333333;
}

[data-theme="dark"] {
  --background-color: #1a1a1a;
  --text-color: #ffffff;
}
```

### 반응형 디자인
```css
/* 미디어 쿼리 */
@media (max-width: 768px) {
  .sidebar {
    width: 100%;
  }
}
```

## 인증 시스템

### Google OAuth
```javascript
// Google 로그인 버튼
<GoogleLoginButton 
  clientId={process.env.VITE_GOOGLE_CLIENT_ID}
  onSuccess={handleLoginSuccess}
/>
```

### JWT 토큰 관리
```javascript
// 토큰 파싱 및 검증
const payload = parseJwt(token);
const userInfo = {
  name: payload.name,
  email: payload.email,
  picture: payload.picture
};

// 토큰 만료 확인
const isExpired = isTokenExpired(accessToken);

// 자동 토큰 갱신
const newAccessToken = await refreshAccessToken(refreshToken);

// 인증된 API 요청
const response = await makeAuthenticatedRequest('/api/endpoint', {
  method: 'POST',
  body: JSON.stringify(data)
});

// 로그아웃
await logout(refreshToken);
clearTokens();
```

## Chrome Extension 특화 기능

### Manifest V3
```javascript
// manifest.config.js
export default {
  manifest_version: 3,
  permissions: ['tabs', 'sidePanel', 'scripting', 'activeTab', 'identity', 'storage'],
  host_permissions: ['<all_urls>'],
  background: {
    service_worker: 'src/background.js',
    type: 'module'
  }
}
```

### Service Worker
```javascript
// background.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // 백그라운드 메시지 처리
});
```

### Content Script
```javascript
// contentReady.js
// 페이지 로드 완료 후 실행
document.addEventListener('DOMContentLoaded', () => {
  // 페이지별 특화 기능
});
```

## 배포

### 개발 환경
1. `npm run dev` 실행
2. Chrome에서 `chrome://extensions/` 접속
3. "개발자 모드" 활성화
4. "압축해제된 확장 프로그램을 로드합니다" 클릭
5. `dist` 폴더 선택

### 프로덕션 환경
1. `npm run build` 실행
2. `dist` 폴더를 웹 서버에 배포
3. Chrome Web Store에 업로드 (선택사항)

## 디버깅

### Chrome DevTools
1. 확장 프로그램 아이콘 우클릭
2. "검사" 선택
3. DevTools에서 디버깅

### 로그 확인
```javascript
// 콘솔 로그
console.log('디버그 정보');

// Chrome Extension 로그
chrome.runtime.sendMessage({ type: 'LOG', data: '로그 메시지' });
```

## 개발 가이드라인

### 코드 스타일
- ESLint 규칙 준수
- 함수형 컴포넌트 사용
- Hook 기반 상태 관리

### 성능 최적화
- React.memo 사용
- 불필요한 리렌더링 방지
- 이미지 최적화

### 보안 고려사항
- XSS 방지
- CSP 헤더 설정
- 민감한 정보 암호화