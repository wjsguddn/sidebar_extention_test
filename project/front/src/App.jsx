import { useState } from "react";
import logo from "/icons/128.png";
import "./App.css";

export default function App() {
  const [info, setInfo] = useState("");

  const handleClick = async () => {
    try {
      const [tab] = await chrome.tabs.query({
        active: true,
        lastFocusedWindow: true,
      });
      if (tab) {
        setInfo(`URL: ${tab.url}\nTitle: ${tab.title}`);
      } else {
        setInfo("탭 정보를 찾을 수 없습니다.");
      }
    } catch (e) {
      setInfo(`오류: ${e.message}`);
    }
  };

  return (
    <>
      <div>
        <a
          href="https://app.slack.com/client/T08URE47UKW/C08UHA2JQEA"
          target="_blank"
        >
          <img src={logo} className="logo" alt="logo" />
        </a>
      </div>

      <div className="card">
        <button onClick={handleClick}>탭 정보 보기</button>
        <pre>{info}</pre>
      </div>
    </>
  );
}
