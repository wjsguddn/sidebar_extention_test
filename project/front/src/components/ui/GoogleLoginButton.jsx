import './GoogleLoginButton.css';

const GoogleLoginButton = ({ onLoginStart, onLoginComplete }) => {
  // 성능 최적화를 위한 캐싱
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
  const redirectUri = `https://${chrome.runtime.id}.chromiumapp.org/`;
  
  // 미리 계산된 URL 파라미터들
  const baseAuthParams = {
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: 'code',
    scope: 'openid email profile',
    prompt: 'select_account'
  };

  const handleLogin = () => {
    // 로그인 시작 시 콜백 호출
    if (onLoginStart) {
      onLoginStart();
    }

    // 더 빠른 state 생성 (더 짧은 문자열)
    const state = Math.random().toString(36).substring(2, 8);
    
    // URL 파라미터 최적화
    const params = new URLSearchParams({
      ...baseAuthParams,
      state: state
    });

    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;

    // 즉시 실행을 위한 최적화
    chrome.identity.launchWebAuthFlow(
      {
        url: authUrl,
        interactive: true,
      },
      function(redirectUrl) {
        if (chrome.runtime.lastError) {
          if (onLoginComplete) {
            onLoginComplete();
          }
          return;
        }
        
        const url = new URL(redirectUrl);
        const code = url.searchParams.get('code');

        if (code) {
          fetch('http://localhost:8000/auth/google', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
          })
          .then(res => res.json())
          .then(data => {
            // JWT 저장
            chrome.storage.local.set({ token: data.token }, () => {
              console.log('로그인 성공:', data);
              // 로그인 완료 시 콜백 호출
              if (onLoginComplete) {
                onLoginComplete();
              }
            });
          })
          .catch(error => {
            console.error('로그인 실패:', error);
            // 에러 발생 시에도 로그인 완료 콜백 호출
            if (onLoginComplete) {
              onLoginComplete();
            }
          });
        } else {
          // 코드가 없는 경우에도 로그인 완료 콜백 호출
          if (onLoginComplete) {
            onLoginComplete();
          }
        }
      }
    );
  };

  return (
    <button className="google-login-btn" onClick={handleLogin}>
      <img src="/icons/google_48.png" alt="Google Logo" className="google-logo" />
      Google 계정으로 로그인
    </button>
  );
};

export default GoogleLoginButton;