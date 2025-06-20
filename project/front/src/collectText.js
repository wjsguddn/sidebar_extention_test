/* export default 함수 : 버튼 수집 및 UI 출력용 */
export default function collectVisibleText() {
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
        // style, script, head, meta 등 무시
        let p = node.parentElement;
        while (p) {
          const tag = p.tagName && p.tagName.toLowerCase();
          if (["script","style","head","meta","title","noscript"].includes(tag)) return NodeFilter.FILTER_REJECT;
          p = p.parentElement;
        }
        // 숨겨진 요소 무시
        if (!isVisible(node)) return NodeFilter.FILTER_REJECT;
        // 빈 텍스트 무시
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

/* 메시지 리스너 : 트리거를 통한 자동 수집용  */
chrome.runtime.onMessage.addListener((msg, _sender, send) => {
  if (msg.type !== "COLLECT_TEXT") return;           // 다른 메시지는 무시
  send({
    url: location.href,
    title: document.title,
    text: collectVisibleText()
  });
  return true;  // async 응답 허용
});

// content script가 주입되어 DOM이 준비된 시점에 background로 알림
chrome.runtime.sendMessage({ type: "CONTENT_READY" });
