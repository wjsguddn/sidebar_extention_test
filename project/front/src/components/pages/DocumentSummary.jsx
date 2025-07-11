import React, { useState, useEffect, useRef } from 'react';
import Card from '../ui/Card';
import './DocumentSummary.css';
import '../ui/CustomScrollbar.css';
import { useWebSocket } from '../../utils/websocketProvider';

export default function DocumentSummary() {
  const [summaryChunks, setSummaryChunks] = useState([]);
  const [finalSummary, setFinalSummary] = useState('');
  const [error, setError] = useState('');
  const { messages, isConnected, isLoading, clearMessages } = useWebSocket();
  const summaryRef = useRef(null);

  // background.js에서 RESET_WEBSOCKET_MESSAGE 메시지를 받으면 메시지 초기화
  useEffect(() => {
    const listener = (msg, sender, sendResponse) => {
      if (msg.type === "RESET_WEBSOCKET_MESSAGE") {
        clearMessages();
      }
    };
    chrome.runtime.onMessage.addListener(listener);
    return () => chrome.runtime.onMessage.removeListener(listener);
  }, [clearMessages]);

  useEffect(() => {
    // WebSocket 메시지 처리
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.type === 'summary_chunk') {
        setSummaryChunks(prev => [...prev, lastMessage.content]);
      } else if (lastMessage.type === 'final_summary') {
        setFinalSummary(lastMessage.content);
      }
    }
  }, [messages]);

  useEffect(() => {
    if (summaryRef.current) {
      summaryRef.current.scrollTop = summaryRef.current.scrollHeight;
    }
  }, [summaryChunks, finalSummary]);

  const clearSummary = () => {
    setSummaryChunks([]);
    setFinalSummary('');
    setError('');
  };

  return (
    <div className="document-summary-page custom-scrollbar">
      <Card>
        <div className="summary-header">
          <h2>Document Summary</h2>
        </div>
        <div className="summary-content">
          {/* Mini Summaries */}
          {summaryChunks.length > 0 && (
            <div className="mini-summaries">
              <h3>Mini Summaries ({summaryChunks.length})</h3>
              <div className="chunks-container" ref={summaryRef}>
                {summaryChunks.map((chunk, index) => (
                  <Card key={index} className="mini-summary-card">
                    <div className="summary-chunk">
                      <span className="chunk-number">{index + 1}.</span>
                      <span className="chunk-content">{chunk}</span>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Final Summary */}
          {finalSummary && (
            <div className="final-summary">
              <Card className="final-summary-card emphasized">
                <h3>Final Summary (WatsonX Granite)</h3>
                <div className="final-summary-content">
                  {finalSummary}
                </div>
              </Card>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
} 