import React, { useState, useEffect } from "react";
import "./Menubar.css";

const Menubar = ({ theme, toggleTheme, userInfo }) => {
  const [open, setOpen] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  
  // 설정 상태들
  const [contentType, setContentType] = useState("default");
  const [contentPeriod, setContentPeriod] = useState("none");
  const [screenshotUsage, setScreenshotUsage] = useState("button-only");

  // 설정값 로드
  useEffect(() => {
    chrome.storage.local.get(['contentType', 'contentPeriod', 'screenshotUsage'], (result) => {
      if (result.contentType) setContentType(result.contentType);
      if (result.contentPeriod) setContentPeriod(result.contentPeriod);
      if (result.screenshotUsage) setScreenshotUsage(result.screenshotUsage);
    });
  }, []);

  // 설정값 저장 함수
  const saveSettings = (key, value) => {
    chrome.storage.local.set({ [key]: value });
  };

  // 팝업 닫기 핸들러 (배경 클릭 시)
  const handleCloseProfile = () => {
    setShowProfile(false);
    setOpen(false); // 드롭다운도 함께 닫기
  };
  const handleCloseSettings = () => {
    setShowSettings(false);
    setOpen(false); // 드롭다운도 함께 닫기
  };

  const handleLogout = () => {
    chrome.storage.local.remove(['token'], () => {
    // JWT를 삭제하면 App.jsx의 useEffect에서 감지 후 isLoggedIn을 자동으로 갱신
    });
  };

  // 설정 변경 핸들러
  const handleContentTypeChange = (value) => {
    setContentType(value);
    saveSettings('contentType', value);
  };

  const handleContentPeriodChange = (value) => {
    setContentPeriod(value);
    saveSettings('contentPeriod', value);
  };

  const handleScreenshotUsageChange = (value) => {
    setScreenshotUsage(value);
    saveSettings('screenshotUsage', value);
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
          <a href="#" className="menu-item" onClick={() => {
            setShowProfile(true);
            setOpen(false); // 프로필 모달 열 때 드롭다운 닫기
          }}>프로필 관리</a>
          <a href="#" className="menu-item" onClick={() => {
            setShowSettings(true);
            setOpen(false); // 설정 모달 열 때 드롭다운 닫기
          }}>설정</a>
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
      {showSettings && (
        <div className="profile-modal-overlay" onClick={handleCloseSettings}>
          <div className="profile-modal settings-modal" onClick={e => e.stopPropagation()}>
            <div className="settings-title">환경설정</div>
            
            <div className="settings-section">
              <div className="settings-label">추천 컨텐츠 유형</div>
              <select 
                className="settings-select" 
                value={contentType}
                onChange={(e) => handleContentTypeChange(e.target.value)}
              >
                <option value="default">기본</option>
                <option value="youtube">유튜브</option>
                <option value="news">뉴스</option>
                <option value="blog">블로그/포스팅</option>
                <option value="academic">학술/연구</option>
                <option value="wiki">위키</option>
              </select>
            </div>
            
            <div className="settings-section">
              <div className="settings-label">컨텐츠 기간 필터</div>
              <select 
                className="settings-select" 
                value={contentPeriod}
                onChange={(e) => handleContentPeriodChange(e.target.value)}
              >
                <option value="none">없음</option>
                <option value="week">일주일</option>
                <option value="month">한달</option>
                <option value="half-year">반년</option>
                <option value="year">1년</option>
              </select>
            </div>
            
            <div className="settings-section">
              <div className="settings-label">추천 시 스크린샷 활용</div>
              <select 
                className="settings-select" 
                value={screenshotUsage}
                onChange={(e) => handleScreenshotUsageChange(e.target.value)}
              >
                <option value="button-only">버튼만</option>
                <option value="button-auto">버튼 및 자동</option>
                <option value="disabled">활용 안함</option>
              </select>
            </div>
            
            <button onClick={handleCloseSettings}>닫기</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Menubar;