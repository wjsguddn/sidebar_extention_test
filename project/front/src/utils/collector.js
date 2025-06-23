// utils/collector.js
// 모든 수집 과정을 담당하는 모듈

export async function collect(tabId) {
  try {
    // 모든 프레임에서 텍스트 수집
    const frames = await chrome.scripting.executeScript({
      target: { tabId, allFrames: true },
      func: () => {
        // 텍스트 수집 로직 (content script context)
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
    
    // url, title은 background에서 직접 가져옴
    const tab = await chrome.tabs.get(tabId);
    
    // 스크린샷 수집
    let screenshot_base64 = "";
    try {
      const capture = await chrome.tabs.captureVisibleTab(tab.windowId, { format: "png" });
      screenshot_base64 = capture.split(",")[1];
    } catch (e) {
      console.error("[collect] 스크린샷 캡처 실패", e);
      screenshot_base64 = "";
    }
    
    // 결과 반환
    return {
      url: tab.url,
      title: tab.title,
      text: texts,
      screenshot_base64
    };
  } catch (e) {
    console.error("[collect] Unexpected error", e);
    return null;
  }
} 