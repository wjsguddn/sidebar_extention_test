import React from "react";
import "./UserProfile.css";

const UserProfile = () => {
  return (
    <div className="user-profile">
      <img className="avatar" src="/icons/g_purple_profile.jpeg" alt="avatar" />
      <span className="username">User님 안녕하세요!</span>
    </div>
  );
};

export default UserProfile; 