import { useState, useEffect, useCallback, useRef } from "react";
import logo from "/icons/le_penseur.png";
import Button from '../ui/Button';
import Card from '../ui/Card';
import './Recommendation.css';
import '../ui/CustomScrollbar.css';
import { useWebSocket } from "../../utils/websocketProvider";
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

export function RecommendationFooterContent({ onClick, setLastMode}) {
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
      if (setLastMode) {setLastMode(PAGE_MODES.RECOMMENDATION);}
      if (onClick) onClick();}}
      className="rec-button" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div>
        {tabInfo.favIconUrl && (
        <img src={tabInfo.favIconUrl} alt="favicon" style={{ width: 18, height: 18, borderRadius: 4 }} />
        )}
        <span style={{ maxWidth: 80, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {tabInfo.title}
        </span>
      </div>
      <span className="gen_rec_text" style={{ marginLeft: 8 }}>
        추천 생성
      </span>
    </Button>
  );
}

export default function Recommendation({ currentUrl, setLastMode, autoRefreshEnabled, setFooterClick }) {
  // 마운트(렌더) 감지
  const isMounted = useRef(false);
  const { messages, clearMessages } = useWebSocket();
  const [cachedResult, setCachedResult] = useState(null);
  const [renderSource, setRenderSource] = useState("websocket");
  const [lastMessages, setLastMessages] = useState(null);
//   const [error, setError] = useState("");
//   const [loading, setLoading] = useState(false);

  // 마운트/URL 변경 시 캐시 조회
  useEffect(() => {
    if (!currentUrl) return;
    const key = `llm_result:recommendation:${currentUrl}`;
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
      const key = `llm_result:recommendation:${url}`;
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
    chrome.runtime.sendMessage({ type: "COLLECT_BROWSER_BY_BUTTON" });
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

  const rawCards = splitStreamCards(fullText);
  const cards = rawCards.map(parseCard);

  return (
    <div className="recommendation-page custom-scrollbar">
      <div className="logo-section">
        <img src={logo} className="logo" alt="logo" />
      </div>

      <div className="result-section">
        {cards.map((card, i) => (
          <Card key={i} className={`card-${card.type.toLowerCase()}` + (card.inProgress ? " writing" : "") }>
            {card.type === "COMMENT" && (
              <div>{card.value}</div>
            )}
            {card.type === "SUMMARY" && (
              <div>{card.value}</div>
            )}
            {card.type === "RECOMMEND" && (
              <div>
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
              </div>
            )}
          </Card>
        ))}
      </div>

    </div>
  );
}
