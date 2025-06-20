chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
});

// src/background.js  Manifest v3, Chrome 116+
const API = import.meta.env.VITE_API_BASE + "/collect";

// 수집 함수: url, title, text, screenshot을 모두 수집하여 반환
async function collect(tabId) {
  try {
    // 텍스트·메타
    const meta = await chrome.tabs.sendMessage(tabId, { type: "COLLECT_TEXT" })
      .catch((e) => { console.error("[collect] Message failed", e); return null; });
    if (!meta) {
      console.warn("[collect] No meta received from content script");
      return null;
    }
    // 전체 페이지 스크린샷
    let shot = null;
    try {
      shot = await chrome.tabs.captureTab(
        tabId,
        { format: "png", captureBeyondViewport: true }
      );
    } catch (e) {
      console.error("[collect] Screenshot failed", e);
    }
    // 결과 반환
    const result = {
      ...meta,
      screenshot_base64: shot ? shot.split(",")[1] : ""
    };
    return result;
  } catch (e) {
    console.error("[collect] Unexpected error", e);
    return null;
  }
}

// 자동 트리거: 탭 로드 완료 · 전환 시 → 백엔드 전송
chrome.tabs.onUpdated.addListener((id, info, tab) => {
  try {
    // info.url 이벤트에는 700ms 딜레이 후 collect
    if (info.url) {
      setTimeout(() => {
        collect(id).then((data) => {
          if (data) sendToBackend(data, 'url');
        });
      }, 700);
    }
    // info.status === 'complete' 이벤트는 즉시 collect
    if (info.status === "complete") {
      collect(id).then((data) => {
        if (data) sendToBackend(data, 'complete');
      });
    }
  } catch (e) {
    console.error("[onUpdated] Unexpected error", e);
  }
});
chrome.tabs.onActivated.addListener(({ tabId }) => {
  try {
    chrome.tabs.get(tabId, t => {
      if (t.status === "complete") {
        collect(tabId).then((data) => {
          if (data) sendToBackend(data);
        });
      }
    });
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
    collect(sender.tab.id).then((data) => {
      if (data) sendToBackend(data, 'content_ready');
    });
  }
  if (msg.type === "COLLECT_ALL") {
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      const tabId = tabs[0]?.id;
      if (!tabId) return sendResponse({ error: "No active tab" });
      // 모든 프레임에서 collectVisibleText 실행
      const frames = await chrome.scripting.executeScript({
        target: { tabId, allFrames: true },
        func: () => {
          // collectText.js의 collectVisibleText와 동일한 코드 (content script context)
          function isVisible(node) {
            if (!node.parentElement) return true;
            const style = window.getComputedStyle(node.parentElement);
            if (
              style.display === 'none' ||
              style.visibility === 'hidden' ||
              node.parentElement.getAttribute('aria-hidden') === 'true'
            ) return false;
            return isVisible(node.parentElement);
          }
          const walker = document.createTreeWalker(
            document.body,
            NodeFilter.SHOW_TEXT,
            {
              acceptNode: function(node) {
                let p = node.parentElement;
                while (p) {
                  const tag = p.tagName && p.tagName.toLowerCase();
                  if (["script","style","head","meta","title","noscript"].includes(tag)) return NodeFilter.FILTER_REJECT;
                  p = p.parentElement;
                }
                if (!isVisible(node)) return NodeFilter.FILTER_REJECT;
                if (!node.textContent.trim()) return NodeFilter.FILTER_REJECT;
                return NodeFilter.FILTER_ACCEPT;
              }
            },
            false
          );
          const out = [];
          while (walker.nextNode()) {
            out.push(walker.currentNode.textContent.trim());
          }
          return out.join("\n");
        }
      });
      // 프레임별 텍스트 합치기
      const texts = frames.map(f => f.result).filter(Boolean).join('\n\n──────── iframe ────────\n\n');
      // url, title, screenshot은 메인 프레임에서만 수집
      const meta = await chrome.tabs.sendMessage(tabId, { type: "COLLECT_TEXT" }).catch(() => null);
      let shot = null;
      try {
        shot = await chrome.tabs.captureTab(
          tabId,
          { format: "png", captureBeyondViewport: true }
        );
      } catch (e) {}
      sendResponse({
        url: meta?.url || "",
        title: meta?.title || "",
        text: texts,
        screenshot_base64: shot ? shot.split(",")[1] : ""
      });
    });
    return true; // async 응답
  }
});
