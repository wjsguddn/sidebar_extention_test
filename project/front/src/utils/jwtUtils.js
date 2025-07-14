export function parseJwt(token) {
    if (!token) return null;
    try {
        // JWT에서 payload 추출
        const base64Url = token.split('.')[1];
        // base64url → base64 변환
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        // base64 디코딩 후 URI 디코딩 → JSON 문자열 변환
        const jsonPayload = decodeURIComponent(
            atob(base64)
            .split('')
            .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
            .join('')
        );
        // JSON 문자열을 객체로 변환
        return JSON.parse(jsonPayload);
    } catch (e) {
        return null;
    }
}