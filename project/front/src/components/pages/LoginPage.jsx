import logo from "/icons/128.png";
import GoogleLoginButton from '../ui/GoogleLoginButton';
import './LoginPage.css';

export default function LoginPage() {
  return (
    <div className="login-page">
      <div className="logo-container">
        <img src={logo} className="logo" alt="logo" />
      </div>
      <div className="login-message">
        <h2>로그인</h2>
      </div>
      <GoogleLoginButton />
    </div>
  );
} 