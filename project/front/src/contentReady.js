// contentReady.js
// content script가 주입되어 DOM이 준비된 시점에 background로 알림
chrome.runtime.sendMessage({ type: "CONTENT_READY" }); 