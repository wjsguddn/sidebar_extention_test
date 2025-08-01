import { useState } from 'react';
import GoogleLoginButton from '../ui/GoogleLoginButton';
import './LoginPage.css';
import logo from "/icons/thinker_l.png";

export default function LoginPage({ theme }) {
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  // theme이 'dark'면 흰색 로고, 아니면 검정 로고
  const logoUrl =
    theme === 'dark'
      ? chrome.runtime.getURL('icons/textLogoW.png')
      : chrome.runtime.getURL('icons/textLogoB.png');

  const handleLoginStart = () => {
    setIsLoggingIn(true);
  };
    
  const handleLoginComplete = () => {
    setIsLoggingIn(false);
  };  

  return (
    <div className="login-page">
      <div className="login-page-section">
        <img src={logo} className="logo" alt="logo" />
        <div
          className="logo-container"
          style={{
            backgroundImage: `url(${logoUrl})`,
            backgroundSize: 'contain',
            backgroundRepeat: 'no-repeat',
            backgroundPosition: 'center'
          }}
        />
        <div className="ment-section1">
            <div className="ment1">
              브라우저 AI 리서치 어시스턴트
            </div>
            <div className="ment2">
              PenseurAI는 질문하지 않아도 제공합니다
            </div>
        </div>

        <div className="login-message">
          <h2>로그인</h2>
        </div>
        <GoogleLoginButton
          onLoginStart={handleLoginStart}
          onLoginComplete={handleLoginComplete}/>
      </div>

      <div className="ment-section2">
        <div className="ment1">
          사용자 데이터는 안전하게 보호됩니다
        </div>
        <a href="https://www.notion.so/PenseurAI-Privacy-Policy-240cdb6aa38e80bc9534d17dee1646ce"
          className="ment2"
          target="_blank"
          rel="noopener noreferrer">
          개인정보 처리방침
        </a>
      </div>


      {/* 로그인 중일 때 반투명 오버레이 */}
      {isLoggingIn && <div className="login-overlay"></div>}
    </div>
  );
}