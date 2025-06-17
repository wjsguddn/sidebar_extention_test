import { useState } from "react";
import logo from "/icons/128.png";
import "./App.css";

export default function App() {
    const [info, setInfo] = useState("");
    const [screenshot, setScreenshot] = useState(null);

    const handleClick = async () => {
        try {   // 탭 정보 가져오기
            const [tab] = await chrome.tabs.query({
                active: true,
                currentWindow: true
            });

            if (tab) {
                setInfo(`URL: ${tab.url}\n\nTitle: ${tab.title}\n`);

                // screenshot
                const imageDataUrl = await chrome.tabs.captureVisibleTab(); // ← base64 PNG
                setScreenshot(imageDataUrl);
            }
            else {
                setInfo("탭 정보를 찾을 수 없습니다.");
                setScreenshot(null);
            }
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
                <strong className='pre-output'>{info}</strong>
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
                <button onClick={handleClick}>탭 정보 보기</button>
            </div>
        </>
    );
}
