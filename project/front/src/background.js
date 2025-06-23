import { collect } from './utils/collector.js';

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
});

// src/background.js  Manifest v3, Chrome 116+
const API = import.meta.env.VITE_API_BASE + "/collect";

// 전역 단일 디바운스 타이머 및 상태
let debounceTimer = null;
let lastTabId = null;
let lastTriggerType = null;

function handleAutoCollect(tabId, triggerType) {
  lastTabId = tabId;
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }
  debounceTimer = setTimeout(() => {
    collect(lastTabId).then((data) => {
      if (data) sendToBackend(data, triggerType);
    });
    debounceTimer = null;
    lastTabId = null;
  }, 1500);
}

// 자동 트리거: 탭 로드 완료 · 전환 시 → 백엔드 전송
chrome.tabs.onUpdated.addListener((id, info, tab) => {
  try {
    if (info.url) handleAutoCollect(id, 'url');
    if (info.status === "complete") handleAutoCollect(id, 'complete');
  } catch (e) {
    console.error("[onUpdated] Unexpected error", e);
  }
});
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

// 버튼 클릭 등에서 메시지로 수집 요청 시 처리
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "CONTENT_READY" && sender.tab && sender.tab.id) {
    handleAutoCollect(sender.tab.id, 'content_ready');
  }
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
