## 프로젝트 이슈 및 해결

# Known Issues - Unsolved

#### 1. 사이드바가 닫힌 상태에서는 정보 수집 및 전송 중단하도록 변경 예정
#### 2. 모드 별 collector 필요

---

# Known Issues - Solved

#### 1. 크롬 내부 페이지(chrome://extensions 등)에는 content script가 주입되지 않아 수집 불가(정상)
#### 2. 여러 트리거 중 마지막만 전송하려면 디바운스 패턴 적용 가능
#### 3. 이벤트 트리거 중 info.url에만 delay를 적용시켜뒀지만 나머지 트리거들도 페이지가 완전히 로드되기 이전에 크롤링 하는 경향이 있음: 마찬가지로 디바운스 패턴으로 해소 가능할거라 예상
#### 4. 보이는 화면만이 아닌 페이지 전체 캡쳐를 위해 captureTab 적용해봤으나 deprecated(ed)된듯: captureVisibleTab으로 변경하여 보이는 화면만 캡쳐할 예정

---

# Solved Issues
## 1. 프로젝트 초기 이슈 및 통합 과정

### 현상
- 프론트엔드(React, Vite)와 백엔드(FastAPI, Kafka, LLM-worker)를 완전히 분리해서 개발함
- UI 버튼을 통한 수집(모니터링용)과, 자동 수집(탭/URL 트리거) 코드 또한 완전히 분리되어 있었음
- 프론트와 백엔드가 따로 동작
- swagger(백엔드)에서 POST 테스트는 잘 되지만, 프론트에서 트리거 기반 자동 전송이 안 됨
- manifest 설정, content script 주입, CORS 등 환경 이슈 발생

### 원인
- 버튼 클릭용 수집 함수와 자동 수집 함수가 별개로 존재(코드 중복)
- manifest.config.js에서 content script 주입, 권한, host_permissions 등 설정 미흡
- CORS 설정 누락, API 주소 오타 등으로 fetch 실패
- swagger에서는 직접 데이터 입력이 가능해 잘 동작했으나, 실제 프론트-백엔드 연동x

### 해결
- **background.js**: collect 함수로 수집 로직 일원화, 버튼 클릭/자동 트리거 모두 이 함수만 사용
  ```js
  async function collect(tabId) { ... }
  chrome.runtime.onMessage.addListener(...)
  chrome.tabs.onUpdated.addListener(...)
  ```
- **App.jsx**: 버튼 클릭 시 background에 메시지 보내서 수집 결과를 받아 UI에 출력
  ```js
  chrome.runtime.sendMessage({ type: "COLLECT_ALL" }, ...)
  ```
- **manifest.config.js**: content script가 모든 탭에 주입되도록 matches, host_permissions 등 보강
  ```js
  content_scripts: [{ matches: ['<all_urls>'], js: ['src/collectText.js'], ... }]
  permissions: ['tabs', 'sidePanel', 'scripting', 'activeTab']
  host_permissions: ['<all_urls>', ...]
  ```
- **CORS, API 주소 등 fetch 관련 이슈**: background.js의 fetch URL, headers 등 점검 및 수정
- **프론트-백엔드 연동**: swagger와 동일한 데이터 구조로 POST 전송 확인

---


## 2. 크롬 확장 자동 수집 누락/중복 이슈

### 현상
- 탭 이동(onActivated)은 잘 동작하지만, URL 이동(onUpdated)은 누락되거나 느림
- 네이버, 유튜브, ChatGPT 등 최초 진입 시 데이터 전송 누락, 내부 이동 시에는 정상 동작
- Slack, Discord, Replit 등 SPA는 항상 잘 동작
- 한 번의 사이트 이동에 여러 번 collect가 발생(중복 전송)

### 원인
- content script가 아직 주입되지 않은 상태에서 collect 시도(최초 진입 시)
- onUpdated(info.url)는 너무 이른 타이밍에 발생해 DOM/content script가 준비되지 않음
- onUpdated(info.status === 'complete')는 여러 번 발생할 수 있음(iframe 등)
- SPA는 내부 라우팅 시 content script가 이미 주입된 상태라 정상 동작

### 해결
- **content script가 주입되어 DOM이 준비된 시점에 background로 'CONTENT_READY' 메시지**
  - collectText.js:
    ```js
    chrome.runtime.sendMessage({ type: "CONTENT_READY" });
    ```
  - background.js:
    ```js
    chrome.runtime.onMessage.addListener((msg, sender, ...) => {
      if (msg.type === "CONTENT_READY" && sender.tab && sender.tab.id) {
        collect(sender.tab.id).then(...)
      }
    });
    ```
- **onUpdated(info.url)에는 700ms 딜레이 후 collect 시도**
  ```js
  if (info.url) {
    setTimeout(() => collect(id).then(...), 700);
  }
  ```
- **onUpdated(info.status === 'complete')는 즉시 collect**
  ```js
  if (info.status === "complete") {
    collect(id).then(...);
  }
  ```
- **세 가지 트리거(content_ready, url, complete) 병행**

---


## 3. content script 텍스트 수집 품질 이슈

### 현상
- CSS, JS, 숨겨진 텍스트 등 의미 없는 텍스트까지 수집됨
- 일부 사이트에서 텍스트가 일부만 수집됨

### 원인
- 단순히 모든 텍스트 노드를 긁어와서 style, script, head, meta, 숨김 요소까지 포함됨
- slice(0, 5000) 등 길이 제한

### 해결
- **style, script, head, meta, title, noscript 등 무시**
- **display: none, visibility: hidden, aria-hidden="true" 등 숨김 요소 무시**
- **iframe까지 포함해 모든 프레임에서 텍스트 수집(버튼 클릭 시)**
  - collectText.js:
    ```js
    // NodeFilter.SHOW_TEXT + acceptNode에서 태그/스타일/숨김 필터링
    // 마지막에 .join("\n") (slice 제거)
    ```
  - background.js:
    ```js
    // chrome.scripting.executeScript({ allFrames: true, ... })로 프레임별 텍스트 합치기
    ```

---


