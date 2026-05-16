import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { connectWS } from '../api';
import ProgressBar from '../components/ProgressBar';

function ProcessingPage({ token }) {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const [stage, setStage] = useState('');
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('connecting');

  useEffect(() => {
    const ws = connectWS(taskId, (data) => {
      console.log('WebSocket message:', data);

      if (data.stage) {
        setStage(data.stage);
      }

      if (data.progress !== undefined) {
        setProgress(data.progress);
      }

      if (data.status) {
        setStatus(data.status);
      }

      // 处理完成，跳转到结果页
      if (data.status === 'completed') {
        setTimeout(() => {
          navigate('/results');
        }, 1500);
      }
    });

    ws.onopen = () => {
      setStatus('connected');
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setStatus('error');
    };

    ws.onclose = () => {
      setStatus('disconnected');
    };

    return () => {
      ws.close();
    };
  }, [taskId, navigate]);

  return (
    <div className="processing-page">
      <div className="processing-container">
        <h2>处理中</h2>

        <div className="status-card">
          <div className="stage-name">{stage || '连接中...'}</div>

          <ProgressBar
            progress={progress}
            status={status}
            stages={['初始化', '图片分析', '精选照片', '生成故事']}
          />

          <div className="status-message">
            {status === 'connecting' && '正在连接服务器...'}
            {status === 'connected' && `处理进度：${progress}%`}
            {status === 'completed' && '处理完成！正在跳转...'}
            {status === 'error' && '处理出错，请重试'}
          </div>
        </div>

        <div className="processing-spinner">
          <div className="spinner-circle"></div>
          <div className="spinner-circle"></div>
          <div className="spinner-circle"></div>
        </div>
      </div>
    </div>
  );
}

export default ProcessingPage;
