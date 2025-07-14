import { useState, useEffect, useCallback } from "react";
import logo from "/icons/le_penseur.png";
import Button from '../ui/Button';
import Card from '../ui/Card';
import './Recommendation.css';
import '../ui/CustomScrollbar.css';
import { useWebSocket } from "../../utils/websocketProvider";

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

export function RecommendationFooterContent({ onClick }) {
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
    <Button onClick={onClick} className="rec-button" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div>
        {tabInfo.favIconUrl && (
        <img src={tabInfo.favIconUrl} alt="favicon" style={{ width: 18, height: 18, borderRadius: 4 }} />
        )}
        <span style={{ maxWidth: 80, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {tabInfo.title}
        </span>
      </div>
      <span className="gen_rec_text" style={{ marginLeft: 8, fontWeight: 500 }}>
        추천 생성
      </span>
    </Button>
  );
}

export default function Recommendation({ setFooterClick }) {
  const [info, setInfo] = useState("");
  const [screenshot, setScreenshot] = useState(null);
  const { messages, clearMessages } = useWebSocket();

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
    try {
      chrome.runtime.sendMessage({ type: "COLLECT_BROWSER_BY_BUTTON" }, (result) => {
        if (!result || result.error) {
          setInfo(`오류: ${result?.error || '수집 실패'}`);
          setScreenshot(null);
          return;
        }
        const { url, title, text, screenshot_base64 } = result;
        setInfo(`URL:\n${url}\n\nTitle:\n${title}\n\nText:\n${text}`);
        setScreenshot(screenshot_base64 ? `data:image/png;base64,${screenshot_base64}` : null);
      });
    } catch (e) {
      setInfo(`오류: ${e.message}`);
      setScreenshot(null);
    }
  }, [clearMessages]);

  // Footer 버튼 핸들러를 App에 연결
  useEffect(() => {
    if (setFooterClick) {
      setFooterClick(() => handleClick);
    }
  }, [setFooterClick, handleClick]);

  const fullText = messages.map(msg => msg.content).join("");
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
                  {card.url && (
                    <a href={card.url} target="_blank" rel="noopener noreferrer">{card.url}</a>
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