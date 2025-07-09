import GoogleLoginButton from '../ui/GoogleLoginButton';
import './LoginPage.css';

export default function LoginPage({ theme }) {
  // theme이 'dark'면 흰색 로고, 아니면 검정 로고
  const logoUrl =
    theme === 'dark'
      ? chrome.runtime.getURL('icons/textLogoW.png')
      : chrome.runtime.getURL('icons/textLogoB.png');

  return (
    <div className="login-page">
      <div
        className="logo-container"
        style={{
          backgroundImage: `url(${logoUrl})`,
          width: '80%', // 원하는 크기로 조정
          height: '8%',
          backgroundSize: 'contain',
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'center'
        }}
      />
      <div className="login-message">
        <h3>로그인</h3>
      </div>
      <GoogleLoginButton />
    </div>
  );
}