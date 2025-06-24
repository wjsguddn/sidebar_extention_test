import React from "react";
import "./Header.css";
import UserProfile from "./UserProfile";
import Menubar from "./Menubar";

const Header = () => {
  return (
    <header className="header">
      <UserProfile />
      <Menubar />
    </header>
  );
};

export default Header; 