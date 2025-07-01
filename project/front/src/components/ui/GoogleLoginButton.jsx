import './GoogleLoginButton.css';

const GoogleLoginButton = () => {
  const handleLogin = () => {
    const clientId = '285174959230-3jq3rj01h2rc183de6196gocpe49c57l.apps.googleusercontent.com';
    const redirectUri = `https://${chrome.runtime.id}.chromiumapp.org/`;
    const scope = 'openid email profile';
    const responseType = 'code';
    const state = Math.random().toString(36).substring(2);  // 매번 새로운 랜덤 문자열 state를 생성하여 중복 요청 방지
    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=${responseType}&scope=${encodeURIComponent(scope)}&state=${state}`;

    chrome.identity.launchWebAuthFlow(
      {
        url: authUrl,
        interactive: true
      },
      function(redirectUrl) {
        if (chrome.runtime.lastError) {
          return;
        }
        const url = new URL(redirectUrl);
        const code = url.searchParams.get('code');
      }
    );
  };

  return (
    <button className="google-login-btn" onClick={handleLogin}>
      <img src="/icons/google_48.png" alt="Google Logo" className="google-logo" />
      Google로 로그인
    </button>
  );
};

export default GoogleLoginButton; 