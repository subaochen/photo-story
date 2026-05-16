import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';

function StoryPage({ token }) {
  const [story, setStory] = useState(null);
  const [currentChapter, setCurrentChapter] = useState(0);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchStory();
  }, []);

  const fetchStory = async () => {
    try {
      const lastTaskId = localStorage.getItem('lastTaskId');
      if (!lastTaskId) {
        setLoading(false);
        return;
      }

      const response = await api('GET', `/tasks/${lastTaskId}/results`, null, token);
      
      if (response.story) {
        setStory(response.story);
      }

      setLoading(false);
    } catch (err) {
      console.error('Fetch story error:', err);
      setLoading(false);
    }
  };

  const handleExport = () => {
    navigate('/export');
  };

  if (loading) {
    return (
      <div className="story-page">
        <div className="loading">生成故事中...</div>
      </div>
    );
  }

  if (!story) {
    return (
      <div className="story-page">
        <div className="empty-state">
          <p>暂无故事内容</p>
          <button onClick={fetchStory} className="retry-btn">
            重新生成
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="story-page">
      <div className="story-container">
        <div className="story-header">
          <h2>{story.title || '照片故事'}</h2>
          <div className="chapter-nav">
            {story.chapters?.map((_, index) => (
              <button
                key={index}
                className={`chapter-btn ${currentChapter === index ? 'active' : ''}`}
                onClick={() => setCurrentChapter(index)}
              >
                第 {index + 1} 章
              </button>
            ))}
          </div>
        </div>

        {story.chapters && story.chapters.length > 0 && (
          <div className="chapter-content">
            <h3>{story.chapters[currentChapter].title}</h3>
            <p>{story.chapters[currentChapter].content}</p>
          </div>
        )}

        {story.images && story.images.length > 0 && (
          <div className="story-images">
            {story.images.map((img, index) => (
              <div key={index} className="story-image">
                <img src={img.url || img} alt={`story-${index}`} />
              </div>
            ))}
          </div>
        )}

        <div className="action-buttons">
          <button className="btn btn-secondary" onClick={handleExport}>
            导出 PDF
          </button>
        </div>
      </div>
    </div>
  );
}

export default StoryPage;
