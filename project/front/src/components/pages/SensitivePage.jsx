import logo from "/icons/128.png";
import './SensitivePage.css';

export default function SensitivePage() {
  return (
    <div className="sensitive-page">
      <div className="logo-container">
        <img src={logo} className="logo" alt="logo" />
      </div>
      <div className="message">
        <h2>민감한 정보 페이지입니다</h2>
        <p>로그인, 회원가입 등 민감한 정보가 포함된 페이지에서는</p>
        <p>개인정보 보호를 위해 데이터 수집을 하지 않습니다.</p>
      </div>
    </div>
  );
} 