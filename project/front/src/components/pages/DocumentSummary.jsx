import React, { useState, useEffect, useCallback, useRef } from 'react';
import logo from "/icons/blue_penseur.png";
import Card from '../ui/Card';
import Button from '../ui/Button';
import './DocumentSummary.css';
import '../ui/CustomScrollbar.css';
import { useWebSocket } from '../../utils/websocketProvider';
import { PAGE_MODES } from '../../utils/constants';


const CARD_REGEX = /__(COMMENT|SUMMARY|RECOMMEND)\|\|\|/g;

function splitStreamCards(streamText) {
  let cards = [];
  let match;
  let lastIndex = 0;
  let lastType = null;

  while ((match = CARD_REGEX.exec(streamText)) !== null) {
    if (lastType) {
      const content = streamText.slice(lastIndex, match.index);
      cards.push({ type: lastType, content });
    }
    lastType = match[1];
    lastIndex = CARD_REGEX.lastIndex;
  }
  if (lastType && lastIndex <= streamText.length) {
    const content = streamText.slice(lastIndex);
    cards.push({ type: lastType, content });
  }
  return cards;
}

function parseCard(card) {
  if (card.type === "RECOMMEND") {
    const [title, desc1, desc2, url] = card.content.split("|||");
    return {
      type: "RECOMMEND",
      title: title?.trim() ?? "",
      desc1: desc1?.trim() ?? "",
      desc2: desc2?.trim() ?? "",
      url: url?.trim() ?? "",
      inProgress: !url,
    };
  } else {
    return {
      type: card.type,
      value: card.content.trim(),
    };
  }
}


export function DocumentSummaryFooterContent({ onClick, setLastMode}) {
  const [tabInfo, setTabInfo] = useState({ title: '', favIconUrl: '' });

  // 탭 정보 수집 함수
  const fetchTabInfo = useCallback(() => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs && tabs[0]) {
        setTabInfo({
          title: tabs[0].title || '',
          favIconUrl: tabs[0].favIconUrl || ''
        });
      }
    });
  }, []);

  useEffect(() => {
    fetchTabInfo(); // 최초 수집

    // 탭 변경/업데이트 이벤트 리스너 등록
    const handleTabChange = () => fetchTabInfo();
    chrome.tabs.onActivated.addListener(handleTabChange);
    chrome.tabs.onUpdated.addListener(handleTabChange);

    // 언마운트 시 리스너 해제
    return () => {
      chrome.tabs.onActivated.removeListener(handleTabChange);
      chrome.tabs.onUpdated.removeListener(handleTabChange);
    };
  }, [fetchTabInfo]);

  return (
    <Button onClick={() => {
      // 페이지 강제 전환
      if (setLastMode) {setLastMode(PAGE_MODES.DOCUMENT);}
      if (onClick) onClick();}}
      className="doc-button" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div>
        {tabInfo.favIconUrl && (
        <img src={tabInfo.favIconUrl} alt="favicon" style={{ width: 18, height: 18, borderRadius: 4 }} />
        )}
        <span style={{ maxWidth: 80, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {tabInfo.title}
        </span>
      </div>
      <span className="gen_doc_text" style={{ marginLeft: 8 }}>
        문서 요약
      </span>
    </Button>
  );
}


export default function DocumentSummary({ currentUrl, setLastMode, autoRefreshEnabled, setFooterClick }) {
  const [summaryChunks, setSummaryChunks] = useState([]);
  const [finalSummary, setFinalSummary] = useState('');
  const [sonarResult, setSonarResult] = useState('');
  const [displayMode, setDisplayMode] = useState('mini');  // 'mini' or 'final'
  const [miniSummary, setMiniSummary] = useState('');
  const [finalSummaryStream, setFinalSummaryStream] = useState('');
  const [error, setError] = useState('');
  const { messages, isConnected, isLoading, clearMessages } = useWebSocket();
  const summaryRef = useRef(null);
  const [sonarStarted, setSonarStarted] = useState(false);

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

  const handleClick = useCallback(async () => {
    clearMessages();
    //setRenderSource("websocket");
    chrome.runtime.sendMessage({ type: "COLLECT_DOCUMENT_BY_BUTTON" });
  }, [clearMessages]);

  // Footer 버튼 핸들러를 App에 연결
  useEffect(() => {
    if (setFooterClick) {
      setFooterClick(() => handleClick);
    }
  }, [setFooterClick]);


  useEffect(() => {
    if (messages.length === 0) return;
    let mini = '';
    let final = '';
    let sonar = '';
    let mode = 'mini';
    // messages를 순차적으로 분기
    messages.forEach(msg => {
      if (msg.type === 'summary_chunk') {
        setSonarStarted(false);
        mode = 'mini';
        mini = msg.content;
        final = '';
        sonar = '';
      } else if (msg.type === 'final_summary_stream') {
        mode = 'final';
        mini = '';
        final += msg.content;
      }
      else if (msg.type === 'sonar_stream') {
        setSonarStarted(true);
        mini = '';
        sonar += msg.content;
      }
    });
    setDisplayMode(mode);
    setMiniSummary(mini);
    setFinalSummaryStream(final);
    setSonarResult(sonar);
  }, [messages]);

  const rawCards = splitStreamCards(sonarResult);
  const cards = rawCards.map(parseCard);

  return (
    <div className="document-summary-page custom-scrollbar">
      <div className="logo-section">
        <img src={logo} className="logo" alt="logo" />
      </div>
      <div className="result-section">
        <Card className="card-comment">
          <div className="summary-section">
            {/* 미니서머리 모드 */}
            {displayMode === 'mini' && !sonarStarted && (
              <div className="mini-summary">
                <div className="doc-ing-text">문서 파악중...</div>
                {miniSummary}
              </div>
            )}
            {cards.map((card, i) =>
              card.type === "COMMENT" && (
                <div>{card.value}</div>
              )
            )}
         </div>
        </Card>

        {displayMode === 'final' && (
          <Card className="final-summary">
            <div className="document-summary-text">Document Summary</div>
            {finalSummaryStream}
          </Card>
        )}

        {cards.map((card, i) =>
          card.type === "RECOMMEND" && (
            <Card className="card-recommend">
              <div className="card-title">{card.title}</div>
              <div className="card-desc1">{card.desc1}</div>
              <div className="card-desc2">{card.desc2}</div>
              <div className="card-url">
                🔗
                {card.url && (
                  <a className="url" href={card.url} target="_blank" rel="noopener noreferrer">{card.url}</a>
                )}
              </div>
              {card.inProgress && <div className="writing-indicator">작성중…</div>}
            </Card>
          )
        )}

      </div>
    </div>
  );
} 