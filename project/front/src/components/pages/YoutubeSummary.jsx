import { useState, useEffect, useCallback, useRef } from "react";
import logo from "/icons/purple_penseur.png";
import Card from '../ui/Card';
import Button from '../ui/Button';
import './YoutubeSummary.css';
import '../ui/CustomScrollbar.css';
import { useWebSocket } from "../../utils/websocketProvider";
import { PAGE_MODES } from '../../utils/constants';
const CARD_REGEX = /__(COMMENT|SUMMARY|TIMELINE)\|\|\|/g;
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
  if (lastType && lastIndex < streamText.length) {
    const content = streamText.slice(lastIndex);
    cards.push({ type: lastType, content });
  }
  return cards;
}
function parseCard(card) {
  if (card.type === "TIMELINE") {
    const lines = card.content
      .split('\n')
      .map(line => line.trim())
      .filter((line, index, self) => line.length > 0 && self.indexOf(line) === index); // 중복 제거
    return {
      type: card.type,
      lines,
    };
  }
  return {
    type: card.type,
    value: card.content.trim(),
  };
}
function mmssToSeconds(timeStr) {
  const parts = timeStr.split(':').map(Number);
  if (parts.length === 2) {
    // MM:SS 형식
    const [min, sec] = parts;
    return min * 60 + sec;
  } else if (parts.length === 3) {
    // H:MM:SS 형식
    const [hour, min, sec] = parts;
    return hour * 3600 + min * 60 + sec;
  }
  return 0; // 잘못된 형식인 경우
}
function SeekTo(seconds) {
  chrome.runtime.sendMessage({ type: "SEEK_TO", seconds });
}
export function YoutubeSummaryFooterContent({ onClick, setLastMode}) {
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
      if (setLastMode) {setLastMode(PAGE_MODES.YOUTUBE);}
      if (onClick) onClick();}}
      className="yt-button" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div>
        {tabInfo.favIconUrl && (
        <img src={tabInfo.favIconUrl} alt="favicon" style={{ width: 18, height: 18, borderRadius: 4 }} />
        )}
        <span style={{ maxWidth: 80, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {tabInfo.title}
        </span>
      </div>
      <span className="gen_yt_text" style={{ marginLeft: 8 }}>
        영상 요약
      </span>
    </Button>
  );
}
export default function YoutubeSummary({ currentUrl, setLastMode, autoRefreshEnabled, setFooterClick }) {
  // 마운트(렌더) 감지
  const isMounted = useRef(false);
  const { messages, clearMessages } = useWebSocket();
  const [messagesF, setMessagesF] = useState("");
  const [cachedResult, setCachedResult] = useState(null);
  const [renderSource, setRenderSource] = useState("websocket");
  const [lastMessages, setLastMessages] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [hasReceivedFirstMessage, setHasReceivedFirstMessage] = useState(false);
  // 마운트/URL 변경 시 캐시 조회
  useEffect(() => {
    if (!currentUrl) return;
    const key = `llm_result:youtube:${currentUrl}`;
    chrome.storage.local.get([key], (items) => {
      if (items[key]) {
        setCachedResult(items[key].result);
        setRenderSource("cache");
        // 모드별 가장 최근 렌더된 content 갱신
        setLastMessages(items[key].result);
      }
      else {
        setCachedResult(null);
        setRenderSource("lastMsg");
      }
    });
  }, [currentUrl]);
  useEffect(() => {
    if (messages.length === 0) return;
    let messages_f = '';
    // messages를 순차적으로 분기
    messages.forEach(msg => {
      if (msg.type === 'youtube') {
        messages_f += msg.content;
      }
    });
    setMessagesF(messages_f);
  }, [messages]);
  // is_final 수신 시 스토리지 갱신
  useEffect(() => {
    if (!isMounted.current) {
      isMounted.current = true;
      return; // 마운트 시에는 실행하지 않음
    }
    if (!messages.length) return;
    const lastMsg = messages[messages.length - 1];
    if (lastMsg.type === "youtube"){ setRenderSource("websocket"); }
    if (lastMsg.is_final_y) {
      const fullText = messages
        .filter(msg => msg.type === "youtube")
        .map(msg => msg.content)
        .join("");
      const key = `llm_result:youtube:${lastMsg.is_final_y}`;
      const value = {
        result: fullText,
        timestamp: Date.now()
      };
      chrome.storage.local.set({ [key]: value }, () => {
        // 저장 완료 후 로그 출력
        console.log(`[chrome.storage.local 저장] key: ${key}`, value);
        setCachedResult(fullText);
        setRenderSource("cache");
        // 모드별 가장 최근 렌더된 content 갱신
        setLastMessages(value.result);
      });
    }
  }, [messages]);
  // 요청 시작 감지
  useEffect(() => {
    const listener = (msg, sender, sendResponse) => {
      if (msg.type === "RESET_WEBSOCKET_MESSAGE") {
        clearMessages();
      }
      if (msg.type === "YOUTUBE_REQUEST_STARTED") {
        setIsLoading(true);
        setHasReceivedFirstMessage(false);
      }
    };
    chrome.runtime.onMessage.addListener(listener);
    return () => chrome.runtime.onMessage.removeListener(listener);
  }, [clearMessages]);

  // 첫 메시지 도착 감지
  useEffect(() => {
    if (messages.length > 0 && !hasReceivedFirstMessage) {
      const firstYoutubeMessage = messages.find(msg => msg.type === 'youtube');
      if (firstYoutubeMessage) {
        setHasReceivedFirstMessage(true);
        setIsLoading(false);
      }
    }
  }, [messages, hasReceivedFirstMessage]);
  const handleClick = useCallback(async () => {
    clearMessages();
    setRenderSource("websocket");
    chrome.runtime.sendMessage({ type: "COLLECT_YOUTUBE_BY_BUTTON" });
  }, [clearMessages]);
  // Footer 버튼 핸들러를 App에 연결
  useEffect(() => {
    if (setFooterClick) {
      setFooterClick(() => handleClick);
    }
  }, [setFooterClick]);
  // 렌더할 데이터 결정
  let fullText = "";
  if (renderSource === "cache" && cachedResult) {
    fullText = cachedResult;
  } else if (renderSource === "websocket") {
    fullText = messagesF
  } else if (renderSource === "lastMsg") {
    fullText = lastMessages;
  }
  //console.log(fullText);
  const rawCards = splitStreamCards(fullText);
  const cards = rawCards.map(parseCard);
  // TIMELINE 카드 중복 제거
  const filteredCards = [];
  const seenTimelineKeys = new Set();
  for (const card of cards) {
    if (card.type === "TIMELINE") {
      // lines가 없는 경우도 대비
      const key = (card.lines || []).join('|');
      if (seenTimelineKeys.has(key)) continue;
      seenTimelineKeys.add(key);
      filteredCards.push(card);
    } else {
      filteredCards.push(card);
    }
  }
//   for (const card of cards) {
//     filteredCards.push(card);
//   }
  return (
    <div className="youtube-summary-page custom-scrollbar">
      <div className="logo-section">
        <img 
          src={logo} 
          className={`logo ${isLoading ? 'loading' : ''}`} 
          alt="logo" 
        />
      </div>
      <div className="result-section">
        {error && (
          <Card>
            <p style={{ color: 'red' }}>{error}</p>
          </Card>
        )}
        {filteredCards.length === 0 && !loading && !error && (
          <Card className="default-card">
            {isLoading 
              ? "영상 분석중..." 
              : "어떤 영상을 찾아보고 계신가요?"
            }
          </Card>
        )}
        {filteredCards.map((card, i) => {
        const cardClass = `card-${card.type.toLowerCase()}`; // card-comment, card-summary, card-timeline
        return (
          <Card key={i} className={cardClass}>
            {card.type === "COMMENT" && <div>{card.value}</div>}
            {card.type === "SUMMARY" && <div><div className="youtube-summary-text">YouTube Summary</div>{card.value}</div>}
            {card.type === "TIMELINE" && (
              <div className="timeline-section">
                {card.lines.map((line, idx) => {
                  // 시간 형식 매칭: MM:SS 또는 H:MM:SS
                  const timeMatch = line.match(/^(\d{1,2}:\d{2}(?::\d{2})?)/);
                  const time = timeMatch ? timeMatch[1] : '';
                  const text = timeMatch ? line.slice(timeMatch[0].length).trim() : line.trim();
                  return (
                    <div key={idx} className="timeline-entry" >
                      <span className="timeline-time"
                      onClick={() => SeekTo(mmssToSeconds(time))}
                      style={{ cursor: 'pointer' }}
                      >
                        {time}
                        </span>
                      <span className="timeline-text">{text}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        );
      })}
    </div>
  </div>
);
}