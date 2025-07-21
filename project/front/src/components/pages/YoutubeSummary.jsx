import { useState, useEffect, useCallback, useRef } from "react";
import logo from "/icons/le_penseur.png";
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
      className="sum-button" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div>
        {tabInfo.favIconUrl && (
        <img src={tabInfo.favIconUrl} alt="favicon" style={{ width: 18, height: 18, borderRadius: 4 }} />
        )}
        <span style={{ maxWidth: 80, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {tabInfo.title}
        </span>
      </div>
      <span className="gen_sum_text" style={{ marginLeft: 8 }}>
        영상 요약
      </span>
    </Button>
  );
}

export default function YoutubeSummary({ currentUrl, setLastMode, autoRefreshEnabled, setFooterClick }) {
  // 마운트(렌더) 감지
  const isMounted = useRef(false);
  const { messages, clearMessages } = useWebSocket();
  const [cachedResult, setCachedResult] = useState(null);
  const [renderSource, setRenderSource] = useState("websocket");
  const [lastMessages, setLastMessages] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

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

  // is_final 수신 시 스토리지 갱신
  useEffect(() => {
    if (!isMounted.current) {
      isMounted.current = true;
      return; // 마운트 시에는 실행하지 않음
    }
    if (!messages.length) return;
    setRenderSource("websocket");
    const url = currentUrl;
    const lastMsg = messages[messages.length - 1];
    if (lastMsg.is_final) {
      const fullText = messages.map(msg => msg.content).join("");
      const key = `llm_result:youtube:${url}`;
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
    fullText = messages.map(msg => msg.content).join("");
  } else if (renderSource === "lastMsg") {
    fullText = lastMessages;
  }

  //console.log(fullText);
  const rawCards = splitStreamCards(fullText);
  const cards = rawCards.map(parseCard);

  // TIMELINE 카드 중복 제거
  const filteredCards = [];
  const seenTimelineKeys = new Set();

  // for (const card of cards) {
  //   if (card.type === "TIMELINE") {
  //     // lines가 없는 경우도 대비
  //     const key = (card.lines || []).join('|');
  //     if (seenTimelineKeys.has(key)) continue;
  //     seenTimelineKeys.add(key);
  //     filteredCards.push(card);
  //   } else {
  //     filteredCards.push(card);
  //   }
  // }

  for (const card of cards) {
    filteredCards.push(card);
  }

  return (
    <div className="youtube-summary-page custom-scrollbar">
      <div className="logo-section">
        <img src={logo} className="logo" alt="logo" />
      </div>

      <div className="result-section">
        {error && (
          <Card>
            <p style={{ color: 'red' }}>{error}</p>
          </Card>
        )}

        {filteredCards.length === 0 && !loading && !error && (
          <Card>
            <p>궁금해.. 이 영상이 궁금해..</p>
          </Card>
        )}

        {filteredCards.map((card, i) => {
        const cardClass = `card-${card.type.toLowerCase()}`; // e.g., card-comment, card-summary, card-timeline

        return (
          <Card key={i} className={cardClass}>
            {card.type === "COMMENT" && <div>{card.value}</div>}
            {card.type === "SUMMARY" && <div>{card.value}</div>}
            {card.type === "TIMELINE" && (
              <div>
                {card.lines.map((line, idx) => {
                  const time = line.slice(0, 7);
                  const text = line.slice(7).trim();

                  return (
                    <div key={idx} className="timeline-entry" style={{ marginBottom: '20px' }}>
                      <span className="timeline_time">{time}</span>
                      <span className="timeline_text">{text}</span>
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