import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';

function ResultsPage({ token }) {
  const [images, setImages] = useState([]);
  const [totalOriginal, setTotalOriginal] = useState(0);
  const [totalSelected, setTotalSelected] = useState(0);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchResults();
  }, []);

  const fetchResults = async () => {
    try {
      // 这里需要根据实际的任务ID获取，假设从 localStorage 获取
      const lastTaskId = localStorage.getItem('lastTaskId');
      if (!lastTaskId) {
        setLoading(false);
        return;
      }

      const response = await api('GET', `/tasks/${lastTaskId}`, null, token);
      
      if (response.results) {
        setImages(response.results.images || []);
        setTotalOriginal(response.results.total_original || 0);
        setTotalSelected(response.results.total_selected || 0);
      }

      setLoading(false);
    } catch (err) {
      console.error('Fetch results error:', err);
      setLoading(false);
    }
  };

  const handleGenerateStory = async () => {
    const lastTaskId = localStorage.getItem('lastTaskId');
    if (!lastTaskId) return;

    try {
      await api('POST', `/tasks/${lastTaskId}/story`, {}, token);
      navigate('/story');
    } catch (err) {
      console.error('Generate story error:', err);
      alert('生成故事失败');
    }
  };

  const handleExport = () => {
    navigate('/export');
  };

  if (loading) {
    return (
      <div className="results-page">
        <div className="loading">加载中...</div>
      </div>
    );
  }

  return (
    <div className="results-page">
      <div className="results-container">
        <div className="results-header">
          <h2>精选结果</h2>
          <div className="stats">
            <span>原始照片：{totalOriginal} 张</span>
            <span>精选照片：{totalSelected} 张</span>
          </div>
        </div>

        {images.length > 0 ? (
          <div className="image-grid">
            {images.map((img, index) => (
              <div key={index} className="image-item">
                <img src={img.url || img} alt={`result-${index}`} />
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <p>暂无精选照片</p>
            <button onClick={fetchResults} className="retry-btn">
              重新加载
            </button>
          </div>
        )}

        <div className="action-buttons">
          <button
            className="btn btn-primary"
            onClick={handleGenerateStory}
            disabled={images.length === 0}
          >
            生成故事
          </button>
          <button className="btn btn-secondary" onClick={handleExport}>
            导出
          </button>
        </div>
      </div>
    </div>
  );
}

export default ResultsPage;
