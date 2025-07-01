import React, { useState, useEffect } from "react";
import "./Menubar.css";

const Menubar = () => {
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
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
          <a href="#" className="menu-item">프로필 관리</a>
          <a href="#" className="menu-item">설정</a>
          <div className="menu-item" style={{display:'flex',alignItems:'center',justifyContent:'space-between'}}>
            다크모드
            <label className="theme-toggle-switch">
              <input type="checkbox" checked={theme === 'dark'} onChange={toggleTheme} />
              <span className="slider"></span>
            </label>
          </div>
        </div>
      )}
    </div>
  );
};

export default Menubar; 