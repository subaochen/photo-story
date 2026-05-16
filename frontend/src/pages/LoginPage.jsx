import React, { useState } from 'react';
import { API_BASE } from '../api';

function LoginPage({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const endpoint = isRegister ? '/auth/register' : '/auth/login';
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (response.ok) {
        onLogin(data.token || data.access_token, username);
      } else {
        setError(data.detail || data.message || '操作失败');
      }
    } catch (err) {
      setError('网络错误，请稍后重试');
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <h1>PhotoStory</h1>
          <p>{isRegister ? '注册账号' : '登录账号'}</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="username">用户名</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="请输入用户名"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">密码</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              required
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" className="submit-btn">
            {isRegister ? '注册' : '登录'}
          </button>
        </form>

        <div className="toggle-link">
          {isRegister ? (
            <p>
              已有账号？<span onClick={() => setIsRegister(false)}>去登录</span>
            </p>
          ) : (
            <p>
              没有账号？<span onClick={() => setIsRegister(true)}>去注册</span>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
