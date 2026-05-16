import React, { useState } from 'react';

export default function ProgressBar({ progress, status, stages }) {
  const currentStageIndex = Math.min(
    Math.floor((progress / 100) * stages.length),
    stages.length - 1
  );

  return (
    <div className="progress-bar">
      <div className="progress-track">
        <div
          className="progress-fill"
          style={{
            width: `${progress}%`,
            backgroundColor: status === 'error' ? '#ff4444' : '#4CAF50',
          }}
        ></div>
      </div>
      <div className="stages">
        {stages.map((stage, index) => (
          <div
            key={index}
            className={`stage ${index <= currentStageIndex ? 'completed' : ''}`}
          >
            <div className="stage-indicator">
              {index <= currentStageIndex && <span className="check">✓</span>}
            </div>
            <span className="stage-name">{stage}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
