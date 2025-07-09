import logo from "/icons/p_dot.png";
import './DefaultPage.css';

export default function DefaultPage() {
  return (
    <div className="default-page">
      <div className="logo-container">
        <img src={logo} className="logo" alt="logo" />
      </div>
      <div className="message">
        <h2>지원하지 않는 페이지입니다</h2>
        <p>크롬 내부 페이지나 특정 사이트에서는 기능을 사용할 수 없습니다.</p>
      </div>
    </div>
  );
} 