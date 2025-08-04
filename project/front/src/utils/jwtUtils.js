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

export function isTokenExpired(token) {
    if (!token) return true;
    
    const payload = parseJwt(token);
    if (!payload || !payload.exp) return true;
    
    // exp는 초 단위이므로 1000을 곱해서 밀리초로 변환
    const expirationTime = payload.exp * 1000;
    const currentTime = Date.now();
    
    return currentTime >= expirationTime;
}

export async function refreshAccessToken(refreshToken) {
    try {
        const response = await fetch('/auth/refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh_token: refreshToken })
        });
        
        if (response.ok) {
            const data = await response.json();
            return data.access_token;
        }
        return null;
    } catch (error) {
        console.error('Token refresh failed:', error);
        return null;
    }
}

export async function logout(refreshToken) {
    try {
        await fetch('/auth/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh_token: refreshToken })
        });
    } catch (error) {
        console.error('Logout failed:', error);
    }
}

export function getStoredTokens() {
    const accessToken = localStorage.getItem('access_token');
    const refreshToken = localStorage.getItem('refresh_token');
    return { accessToken, refreshToken };
}

export function storeTokens(accessToken, refreshToken) {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
}

export function clearTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
}

export async function makeAuthenticatedRequest(url, options = {}) {
    const { accessToken, refreshToken } = getStoredTokens();
    
    // 기본 헤더 설정
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    // Access token이 있으면 Authorization 헤더 추가
    if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`;
    }
    
    try {
        const response = await fetch(url, {
            ...options,
            headers
        });
        
        // 401 에러 발생 시 토큰 갱신 시도
        if (response.status === 401 && refreshToken) {
            const newAccessToken = await refreshAccessToken(refreshToken);
            
            if (newAccessToken) {
                // 새로운 access token으로 재시도
                storeTokens(newAccessToken, refreshToken);
                headers['Authorization'] = `Bearer ${newAccessToken}`;
                
                return await fetch(url, {
                    ...options,
                    headers
                });
            } else {
                // Refresh token도 만료됨 - 로그아웃 처리
                clearTokens();
                throw new Error('Authentication failed');
            }
        }
        
        return response;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}