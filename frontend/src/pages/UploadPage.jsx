import React, { useState, useCallback } from 'react';
import { api } from '../api';

function UploadPage({ token, onFilesSelected, onTaskCreated }) {
  const [files, setFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const validateFile = (file) => {
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/heic'];
    return validTypes.includes(file.type);
  };

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const newFiles = Array.from(e.dataTransfer.files).filter(validateFile);
        setFiles((prev) => [...prev, ...newFiles]);
        onFilesSelected([...files, ...newFiles]);
      }
    },
    [files, onFilesSelected],
  );

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files).filter(validateFile);
      setFiles((prev) => [...prev, ...newFiles]);
      onFilesSelected([...files, ...newFiles]);
    }
  };

  const removeFile = (index) => {
    const newFiles = [...files];
    newFiles.splice(index, 1);
    setFiles(newFiles);
    onFilesSelected(newFiles);
  };

  const handleStartProcessing = async () => {
    if (files.length === 0) return;

    setUploading(true);
    setProgress(0);

    try {
      const totalSize = files.reduce((sum, file) => sum + file.size, 0);
      const totalChunks = Math.ceil(totalSize / (1024 * 1024)); // 1MB chunks

      // 初始化上传
      const initResponse = await api(
        'POST',
        '/upload/initiate',
        {
          filename: files[0].name,
          total_size: totalSize,
          total_chunks: totalChunks,
        },
        token,
      );

      const taskId = initResponse.task_id;

      // 上传每个文件（简化版：直接上传为单个文件）
      const formData = new FormData();
      files.forEach((file) => {
        formData.append('file', file);
      });

      // 这里需要根据后端实际的 multipart 上传方式调整
      // 假设后端接受多文件上传
      const uploadResponse = await fetch('http://localhost:8000/api/v1/upload/chunk', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const uploadData = await uploadResponse.json();

      if (uploadResponse.ok) {
        // 完成上传
        const completeResponse = await api(
          'POST',
          '/upload/complete',
          { task_id: taskId, top_k: 10 },
          token,
        );

        if (completeResponse.ok) {
          onTaskCreated(taskId);
        }
      }
    } catch (err) {
      console.error('Upload error:', err);
      alert('上传失败，请重试');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-page">
      <div className="upload-container">
        <h2>上传照片</h2>
        <p>拖拽照片到此处，或点击选择文件</p>

        <div
          className={`drop-zone ${dragActive ? 'active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            type="file"
            multiple
            accept=".jpg,.jpeg,.png,.heic"
            onChange={handleFileInput}
            className="file-input"
          />
          <p>拖拽照片到此处，或点击选择文件</p>
          <p className="hint">支持格式：JPG, PNG, HEIC</p>
        </div>

        {files.length > 0 && (
          <div className="file-list">
            <h3>已选择 {files.length} 张照片</h3>
            <div className="file-grid">
              {files.map((file, index) => (
                <div key={index} className="file-item">
                  <img
                    src={URL.createObjectURL(file)}
                    alt={file.name}
                    className="thumbnail"
                  />
                  <span className="filename">{file.name}</span>
                  <button
                    onClick={() => removeFile(index)}
                    className="remove-btn"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {files.length > 0 && (
          <button
            className="start-btn"
            onClick={handleStartProcessing}
            disabled={uploading}
          >
            {uploading ? '处理中...' : '开始处理'}
          </button>
        )}
      </div>
    </div>
  );
}

export default UploadPage;
