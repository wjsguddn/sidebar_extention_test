import React from "react";
import "./UserProfile.css";

const UserProfile = ({userInfo}) => {
  return (
    <div className="user-profile">
      <img className="avatar" src={userInfo.picture} alt="avatar" />
      <span className="username">{userInfo.name}</span>님 안녕하세요!
    </div>
  );
};

export default UserProfile; 