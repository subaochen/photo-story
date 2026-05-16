import React from 'react';
import { useNavigate } from 'react-router-dom';

function ExportPage({ token }) {
  const navigate = useNavigate();

  const handleDownloadPDF = () => {
    // 调用后端导出接口
    alert('PDF 下载功能待实现');
  };

  const handleDownloadVideo = () => {
    alert('视频导出功能待实现');
  };

  return (
    <div className="export-page">
      <div className="export-container">
        <h2>导出</h2>

        <div className="export-options">
          <div className="export-option">
            <div className="option-icon">📄</div>
            <div className="option-info">
              <h3>PDF 相册</h3>
              <p>高质量 PDF 格式，适合打印和分享</p>
            </div>
            <button className="btn btn-primary" onClick={handleDownloadPDF}>
              下载 PDF
            </button>
          </div>

          <div className="export-option">
            <div className="option-icon">🎥</div>
            <div className="option-info">
              <h3>视频演示</h3>
              <p>自动播放的照片故事视频</p>
            </div>
            <button className="btn btn-secondary" onClick={handleDownloadVideo}>
              下载视频
            </button>
          </div>

          <div className="export-option">
            <div className="option-icon">📱</div>
            <div className="option-info">
              <h3>小程序分享</h3>
              <p>生成小程序卡片，微信分享</p>
            </div>
            <button className="btn btn-secondary">分享</button>
          </div>
        </div>

        <div className="back-link">
          <button onClick={() => navigate(-1)} className="btn btn-text">
            ← 返回
          </button>
        </div>
      </div>
    </div>
  );
}

export default ExportPage;
