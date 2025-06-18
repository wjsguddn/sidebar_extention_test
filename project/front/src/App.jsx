import { useState } from "react";
import logo from "/icons/128.png";
import textCollector from './collectText.js';
import "./App.css";

export default function App() {
    const [info, setInfo] = useState("");   // URL, Title, Text
    const [screenshot, setScreenshot] = useState(null);

    const handleClick = async () => {
        // 탭 정보 가져오기
        try {
            const [{id: tabId, url, title}] = await chrome.tabs.query({
                active: true,
                currentWindow: true
            });

            // screenshot
            const imageDataUrl = await chrome.tabs.captureVisibleTab(); // base64 PNG
            setScreenshot(imageDataUrl);

            // 모든 프레임에 textCollector 주입 & 실행
            const frames = await chrome.scripting.executeScript({
                target: { tabId, allFrames: true },
                func: textCollector,            // collectTextRaw.js 에서 export한 함수
            });

            // frames = [{frameId, result: '...'}, ...]  → 결과 합치기
            const texts = frames.map(f => f.result)
                                .filter(Boolean)
                                .join('\n\n──────── iframe ────────\n\n');

            setInfo(`URL:\n${url}\n\nTitle:\n${title}\n\nText:\n${texts}`);
 //           setInfo(`URL:\n${url}\n\nTitle:\n${title}`);
        }
        catch (e) {
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
