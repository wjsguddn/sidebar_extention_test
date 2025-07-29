import { collectBrowser } from './utils/browserCollector.js';
import { documentCollector } from './utils/documentCollector.js';
import { getPageMode } from './utils/pageMode';

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
});

// src/background.js  Manifest v3, Chrome 116+
let API = import.meta.env.VITE_API_BASE + "/collect/browser";

let autoRefreshEnabled = false;


function getTab(tabId) {
  return new Promise((resolve) => {
    chrome.tabs.get(tabId, (tab) => resolve(tab));
  });
}

function getStorage(keys) {
  return new Promise((resolve) => {
    chrome.storage.local.get(keys, (items) => resolve(items));
  });
}


// 전역 단일 디바운스 타이머 및 상태
let debounceTimer = null;
// url 이벤트 윈도우 관리
let lastSentUrl = null;
let lastSentTime = 0;
// 자동 수집 트리거 관리: handleBrowserAutoCollect
async function handleBrowserAutoCollect(tabId, triggerType) {
  if (!autoRefreshEnabled) return;
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(async () => {
    const tab = await getTab(tabId);
    const url = tab.url;
    const mode = getPageMode(url);
    const now = Date.now();

    if (mode === "default" || mode === "sensitive") {
      debounceTimer = null;
      return;
    }

    const keyRec = `llm_result:recommendation:${url}`;
    const keyYt = `llm_result:youtube:${url}`;
    const keyDc = `llm_result:document:${url}`;
    const items = await getStorage([keyRec, keyYt, keyDc]);
    if (items[keyRec] || items[keyYt] || items[keyDc]) {
      debounceTimer = null;
      return;
    }
    if (url === lastSentUrl && now - lastSentTime < 10000) {
      debounceTimer = null;
      return;
    }
    lastSentUrl = url;
    lastSentTime = now;

    if (mode === "recommendation") {
      const data = await collectBrowser(tabId);
      if (data) {
        chrome.runtime.sendMessage({ type: "RESET_WEBSOCKET_MESSAGE" });
        sendToBackend(data, triggerType, mode);
      }
    } else if (mode === "youtube") {
      chrome.runtime.sendMessage({ type: "RESET_WEBSOCKET_MESSAGE" });
      sendToBackend({ youtube_url: url, title: tab.title }, triggerType, mode);
    } else if (mode === "document") {
      const data = await documentCollector(url);
      if (data) {
        chrome.runtime.sendMessage({ type: "RESET_WEBSOCKET_MESSAGE" });
        sendToBackendDoc(data, triggerType, url);
      }
    }
    debounceTimer = null;
  }, 2500);
}


// 자동 트리거: 탭 로드 완료 (url, complete)
chrome.tabs.onUpdated.addListener((id, info, tab) => {
  try {
    // info.url이 있을 때
    if (info.url && tab && tab.url) {
      const mode = getPageMode(tab.url);
      //console.log('url',mode);
      setTimeout(() => handleBrowserAutoCollect(id, 'url'), 500);
    }
    // status가 complete일 때 (tab.url이 있을 때만)
    if (info.status === "complete" && tab && tab.url) {
      const mode = getPageMode(tab.url);
      //console.log('complete',mode);
      handleBrowserAutoCollect(id, 'complete');
    }
  } catch (e) {
    console.error("[onUpdated] Unexpected error", e);
  }
});

// 자동 트리거: 탭 전환 (tab)
chrome.tabs.onActivated.addListener(({ tabId }) => {
  try {
    handleBrowserAutoCollect(tabId, 'tab');
  } catch (e) {
    console.error("[onActivated] Unexpected error", e);
  }
});


// 백엔드 전송 함수
async function sendToBackend(data, triggerType, mode) {
  if (!data) return;

  if (mode === "recommendation") { API = import.meta.env.VITE_API_BASE + "/collect/browser"; }
  else if (mode === "youtube") { API = import.meta.env.VITE_API_BASE + "/collect/youtube"; }

  // JWT 읽기
  chrome.storage.local.get(['token'], async (result) => {
    const token = result.token;
    try {
      await fetch(API, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": token ? `Bearer ${token}` : undefined
        },
        body: JSON.stringify({ ...data, trigger_type: triggerType })
      });
      console.log(`[sendToBackend] Data sent (trigger: ${triggerType}  mode: ${mode})`);
    } catch (e) {
      console.error("[sendToBackend] Failed", e);
    }
  });
}

// doc 백엔드 전송 함수
async function sendToBackendDoc(data, triggerType, pdfUrl) {
  if (!data) return;

  // JWT 읽기
  chrome.storage.local.get(['token'], async (result) => {
    const token = result.token;
    try {
      const blob = data;

      const formData = new FormData();
      formData.append("file", blob, "document.pdf");
      formData.append("fast", "true");
      formData.append("pdf_url", pdfUrl);

      const response = await fetch(import.meta.env.VITE_API_BASE + "/collect/doc", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        },
        body: formData,
      });
      console.log(`[sendToBackend] Data sent (trigger: ${triggerType}  mode: document)`);
      const result = await response.json();
      console.log("추출된 텍스트:", result);
    } catch (error) {
      console.error("PDF 처리 중 오류:", error);
    }
  });
}


chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  // 자동 갱신 토글
  if (msg.type === "AUTO_REFRESH_ENABLED") {
    autoRefreshEnabled = msg.value;
  }
// DOM 준비: content_script에서 CONTENT_READY 메시지
  if (msg.type === "CONTENT_READY" && sender.tab && sender.tab.id) {
    handleBrowserAutoCollect(sender.tab.id, 'content_ready');
  }
// 버튼 클릭 메시지 수집 요청 시 처리
  if (msg.type === "COLLECT_BROWSER_BY_BUTTON") {
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      const tabId = tabs[0]?.id;
      if (!tabId) return sendResponse({ error: "No active tab" });

      const data = await collectBrowser(tabId);
      if (data) {
        sendToBackend(data, 'button', "recommendation");
        sendResponse(data);
      } else {
        sendResponse({ error: "Collection failed" });
      }
    });
    return true; // async 응답
  }

  if (msg.type === "COLLECT_YOUTUBE_BY_BUTTON") {
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      const tabId = tabs[0]?.id;
      if (!tabId) return sendResponse({ error: "No active tab" });

      const tab = await getTab(tabId);
      const data = { youtube_url: tab.url, title: tab.title };
      if (data.youtube_url) {
        sendToBackend(data, 'button', "youtube");
        sendResponse(data);
      } else {
        sendResponse({ error: "Collection failed" });
      }
    });
    return true; // async 응답
  }

  if (msg.type === "COLLECT_DOCUMENT_BY_BUTTON") {
  chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
    const tabId = tabs[0]?.id;
    if (!tabId) return sendResponse({ error: "No active tab" });

    chrome.tabs.get(tabId, (tab) => {
      (async () => {
        const data = await documentCollector(tab.url);
        if (data) {
          sendToBackendDoc(data, 'button', tab.url);
          sendResponse(data);
        } else {
          sendResponse({ error: "Collection failed" });
        }
      })();
    });
  });
  return true; // async 응답
}

});
