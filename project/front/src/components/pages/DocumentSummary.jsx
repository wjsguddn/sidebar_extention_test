import React, { useState, useEffect, useRef } from 'react';
import logo from "/icons/le_penseur.png";
import Card from '../ui/Card';
import Button from '../ui/Button';
import './DocumentSummary.css';
import '../ui/CustomScrollbar.css';
import { useWebSocket } from '../../utils/websocketProvider';
import { PAGE_MODES } from '../../utils/constants';

export default function DocumentSummary() {
  const [summaryChunks, setSummaryChunks] = useState([]);
  const [finalSummary, setFinalSummary] = useState('');
  const [displayMode, setDisplayMode] = useState('mini');  // 'mini' or 'final'
  const [miniSummary, setMiniSummary] = useState('');
  const [finalSummaryStream, setFinalSummaryStream] = useState('');
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
    if (messages.length === 0) return;
    let mini = '';
    let final = '';
    let mode = 'mini';
    // messages를 순차적으로 분기
    messages.forEach(msg => {
      if (msg.type === 'summary_chunk') {
        mode = 'mini';
        mini = msg.content;
        final = '';
      } else if (msg.type === 'final_summary_stream') {
        mode = 'final';
        mini = '';
        final += msg.content;
      }
    });
    setDisplayMode(mode);
    setMiniSummary(mini);
    setFinalSummaryStream(final);
  }, [messages]);


  return (
    <div className="document-summary-page custom-scrollbar">
      <div className="logo-section">
        <img src={logo} className="logo" alt="logo" />
      </div>
      <div className="result-section">
        <Card>
          <div className="summary-section">
            {/* 미니서머리 모드 */}
            {displayMode === 'mini' && (
              <div className="mini-summary">
                <div className="doc-ing-text">문서 파악중...</div>
                {miniSummary}
              </div>
            )}

            {/* 파이널서머리 스트림 모드 */}
            {displayMode === 'final' && (
              <div className="final-summary">
                {finalSummaryStream}
              </div>
            )}
         </div>
        </Card>
      </div>
    </div>
  );
} 