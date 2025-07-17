import React, { useState } from "react";
import "./Menubar.css";

const Menubar = ({ theme, toggleTheme, userInfo }) => {
  const [open, setOpen] = useState(false);
  const [showProfile, setShowProfile] = useState(false);

  // 팝업 닫기 핸들러 (배경 클릭 시)
  const handleCloseProfile = () => setShowProfile(false);

  const handleLogout = () => {
    chrome.storage.local.remove(['token'], () => {
    // JWT를 삭제하면 App.jsx의 useEffect에서 감지 후 isLoggedIn을 자동으로 갱신
    });
  };

  return (
    <div
      className="menubar-container"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <div className="hamburger">
        <span></span>
        <span></span>
        <span></span>
      </div>
      {open && (
        <div className="dropdown-menu">
          <a href="#" className="menu-item" onClick={() => setShowProfile(true)}>프로필 관리</a>
          <a href="#" className="menu-item">설정</a>
          <div className="menu-item" style={{display:'flex',alignItems:'center',justifyContent:'space-between'}}>
            다크 모드
            <label className="theme-toggle-switch">
              <input type="checkbox" checked={theme === 'dark'} onChange={toggleTheme} />
              <span className="slider"></span>
            </label>
          </div>
        </div>
      )}
      {showProfile && (
        <div className="profile-modal-overlay" onClick={handleCloseProfile}>
          <div className="profile-modal" onClick={e => e.stopPropagation()}>
            <img className="avatar" src={userInfo.picture} alt="avatar" />
            <p className="user-email">{userInfo.email}</p>
            <div className="profile-section">
              <div className="profile-title">프로필</div>
            </div>
            <div className="profile-section">
              <div className="profile-label">이름</div>
              <div className="profile-value">{userInfo.name}</div>
            </div>
            <div className="profile-section">
              <div className="profile-label">UID</div>
              <div className="profile-value" id="user-id">{userInfo.user_id}</div>
            </div>
            <div className="logout-section">
              <span className="logout-button" onClick={handleLogout}>⎋ 로그아웃</span>
            </div>
            <button onClick={handleCloseProfile}>닫기</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Menubar;