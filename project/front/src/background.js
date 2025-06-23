import { collect } from './utils/collector.js';

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
});

// src/background.js  Manifest v3, Chrome 116+
const API = import.meta.env.VITE_API_BASE + "/collect";


// 전역 단일 디바운스 타이머 및 상태
let debounceTimer = null;
// url 이벤트 윈도우 관리
let lastSentUrl = null;
let lastSentTime = 0;
// 자동 수집 트리거 관리: handleAutoCollect
function handleAutoCollect(tabId, triggerType) {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }
  debounceTimer = setTimeout(() => {
    chrome.tabs.get(tabId, (tab) => {
      const url = tab.url;
      const now = Date.now();
      if (url === lastSentUrl && now - lastSentTime < 3000) {
        debounceTimer = null;
        return;
      }
      lastSentUrl = url;
      lastSentTime = now;
      collect(tabId).then((data) => {
        if (data) sendToBackend(data, triggerType);
      });
      debounceTimer = null;
    });
  }, 1000);
}


// 자동 트리거: 탭 로드 완료 (url, complete)
chrome.tabs.onUpdated.addListener((id, info, tab) => {
  try {
    if (info.url) setTimeout(() => handleAutoCollect(id, 'url'), 500);
    if (info.status === "complete") handleAutoCollect(id, 'complete');
  } catch (e) {
    console.error("[onUpdated] Unexpected error", e);
  }
});

// 자동 트리거: 탭 전환 (tab)
chrome.tabs.onActivated.addListener(({ tabId }) => {
  try {
    handleAutoCollect(tabId, 'tab');
  } catch (e) {
    console.error("[onActivated] Unexpected error", e);
  }
});

// 백엔드 전송 함수
async function sendToBackend(data, triggerType) {
  if (!data) return;
  const API = import.meta.env.VITE_API_BASE + "/collect";
  try {
    await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...data, trigger_type: triggerType })
    });
    console.log(`[sendToBackend] Data sent (trigger: ${triggerType})`);
  } catch (e) {
    console.error("[sendToBackend] Failed", e);
  }
}


chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
// DOM 준비: content_script에서 CONTENT_READY 메시지
  if (msg.type === "CONTENT_READY" && sender.tab && sender.tab.id) {
    handleAutoCollect(sender.tab.id, 'content_ready');
  }
// 버튼 클릭 메시지 수집 요청 시 처리
  if (msg.type === "COLLECT_BY_BUTTON") {
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      const tabId = tabs[0]?.id;
      if (!tabId) return sendResponse({ error: "No active tab" });
      
      const data = await collect(tabId);
      if (data) {
        sendToBackend(data, 'button');
        sendResponse(data);
      } else {
        sendResponse({ error: "Collection failed" });
      }
    });
    return true; // async 응답
  }
});
