import { useState, useEffect } from "react";
import logo from "/icons/p_dot.png";
import Button from '../ui/Button';
import Card from '../ui/Card';
import './Recommendation.css';
import '../ui/CustomScrollbar.css';
import { useWebSocket } from "../../utils/websocketProvider";

export default function Recommendation() {
    const [info, setInfo] = useState("");   // URL, Title, Text
    const [screenshot, setScreenshot] = useState(null); // 스크린샷 이미지
    const { messages, clearMessages } = useWebSocket();

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

    const handleClick = async () => {
        clearMessages();
        try {
            // background.js에 수집 요청 메시지 전송
            chrome.runtime.sendMessage({ type: "COLLECT_BY_BUTTON" }, (result) => {
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
    };

    return (
        <div className="recommendation-page custom-scrollbar">
            <div className="logo-section">
                <img src={logo} className="logo" alt="logo" />
            </div>

            <Card>
                <div className="result-section">{messages.map(msg => msg.content).join("")}</div>
                <Button onClick={handleClick} variant="primary">추천 생성</Button>
            </Card>
        </div>
    );
} 