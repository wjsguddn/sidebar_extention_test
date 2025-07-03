import React from "react";
import "./Header.css";
import UserProfile from "./UserProfile";
import Menubar from "./Menubar";

const Header = ({ theme, toggleTheme }) => {
  return (
    <header className="header">
      <UserProfile />
      <Menubar theme={theme} toggleTheme={toggleTheme} />
    </header>
  );
};

export default Header; 