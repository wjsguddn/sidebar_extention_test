export default function () {
  // 재귀적
  function collect(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      const t = node.textContent.trim();
      return t ? [t] : [];
    }
    if (!node || node.nodeType !== Node.ELEMENT_NODE) return [];

    const st = window.getComputedStyle(node);
    if (st.display === 'none' || st.visibility === 'hidden' || node.hidden) return [];

    let out = [];
    node.childNodes.forEach(child => { out = out.concat(collect(child)); });
    return out;
  }

  // body가 없으면 빈 문자열 반환
  return (document.body ? collect(document.body) : []).join('\n');
}
