import React, { useState } from "react";
import "./Menubar.css";

const Menubar = () => {
  const [open, setOpen] = useState(false);

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
          <a href="#" className="menu-item">다크모드</a>
        </div>
      )}
    </div>
  );
};

export default Menubar; 