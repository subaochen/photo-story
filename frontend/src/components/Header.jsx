import React from 'react';
import { Link } from 'react-router-dom';

function Header({ currentUser, onLogout }) {
  return (
    <header className="header">
      <div className="header-content">
        <div className="logo">
          <Link to="/upload">PhotoStory</Link>
        </div>
        <div className="user-info">
          <span>{currentUser}</span>
          <button onClick={onLogout} className="logout-btn">
            退出
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;
