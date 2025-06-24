import { useState } from "react";
import logo from "/icons/128.png";
import Button from '../ui/Button';
import Card from '../ui/Card';
import './Recommendation.css';

export default function Recommendation() {
    const [info, setInfo] = useState("");   // URL, Title, Text
    const [screenshot, setScreenshot] = useState(null); // 스크린샷 이미지

    const handleClick = async () => {
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
        <div className="recommendation-page">
            <div className="logo-section">
                <a href="https://app.slack.com/client/T08URE47UKW/C08UHA2JQEA" target="_blank">
                    <img src={logo} className="logo" alt="logo" />
                </a>
            </div>

            <Card>
                <Button onClick={handleClick} variant="primary">탭 정보 보기</Button>

                {screenshot && (
                    <div className="screenshot-section">
                        <strong>ScreenShot:</strong>
                        <img
                            src={screenshot}
                            alt="탭 스크린샷"
                            className="screenshot-image"
                        />
                    </div>
                )}
                {/* URL, Title, Text */}
                <strong className='pre-output'>{info}</strong>
            </Card>
        </div>
    );
} 