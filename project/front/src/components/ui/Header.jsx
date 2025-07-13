import React from "react";
import "./Header.css";
import UserProfile from "./UserProfile";
import Menubar from "./Menubar";

const Header = ({ theme, toggleTheme, userInfo }) => {
  return (
    <header className="header">
      <UserProfile userInfo={userInfo}/>
      <Menubar theme={theme} toggleTheme={toggleTheme} userInfo={userInfo}/>
    </header>
  );
};

export default Header; 