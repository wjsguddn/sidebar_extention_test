import { useState } from "react";
import logo from "/icons/128.png";
import "./App.css";

export default function App() {
    const [info, setInfo] = useState("");   // URL, Title, Text
    const [screenshot, setScreenshot] = useState(null);

    const handleClick = async () => {
        try {
            // background.js에 수집 요청 메시지 전송
            chrome.runtime.sendMessage({ type: "COLLECT_ALL" }, (result) => {
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
        <>
            <div>
                <a href="https://app.slack.com/client/T08URE47UKW/C08UHA2JQEA" target="_blank">
                    <img src={logo} className="logo" alt="logo" />
                </a>
            </div>

            <div className="card">
                <button onClick={handleClick}>탭 정보 보기</button>

                {screenshot && (
                    <div style={{ marginTop: "10px" }}>
                        <strong>ScreenShot:</strong>
                        <img
                            src={screenshot}
                            alt="탭 스크린샷"
                            style={{ maxWidth: "100%", border: "1px solid #ccc", marginTop: "6px", marginBottom: "10px" }}
                        />
                    </div>
                )}
                {/* URL, Title, Text */}
                <strong className='pre-output'>{info}</strong>
            </div>
        </>
    );
}
