export function getPageMode(url) {
  if (!url) return "default";
  if (
    url.includes('login') || url.includes('signup') || url.includes('signin') || url.includes('password') || url.includes('account')
  ) {
    return "sensitive";
  }
  if (
    url.startsWith('chrome://') || url.startsWith('chrome-extension://') ||
    url.startsWith('about:') || url.startsWith('moz-extension://')
  ) {
    return "default";
  }
  if (url.includes('.pdf') || url.includes('/pdf') || url.includes('pdf/')) {
    return "document";
  }
  if (url.includes('youtube.com/watch')) {
    return "youtube";
  }
  return "recommendation";
}