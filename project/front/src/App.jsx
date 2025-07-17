import { useState, useEffect, useCallback, useRef } from "react";
import Header from './components/ui/Header';
import Footer from './components/ui/Footer';
import LoginPage from './components/pages/LoginPage';
import DefaultPage from './components/pages/DefaultPage';
import DocumentSummary from './components/pages/DocumentSummary';
import YoutubeSummary from './components/pages/YoutubeSummary';
import Recommendation, { RecommendationFooterContent } from './components/pages/Recommendation';
import SensitivePage from './components/pages/SensitivePage';
import LoadingSpinner from './components/ui/LoadingSpinner';
import AutoRefreshToggleButton from './components/ui/AutoRefreshToggleButton';
import { parseJwt } from './utils/jwtUtils';
import { PAGE_MODES } from './utils/constants';
import { WebSocketProvider } from "./utils/websocketProvider";
import { getPageMode } from './utils/pageMode';
import "./App.css";

export default function App() {
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [userInfo, setUserInfo] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [pageMode, setPageMode] = useState(PAGE_MODES.DEFAULT);
    const [lastMode, setLastMode] = useState(PAGE_MODES.DEFAULT);
    const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(false);
    const getInitialTheme = () => {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) return savedTheme;
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    };
    const [theme, setTheme] = useState(getInitialTheme);

    
    useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }, [theme]);

    const toggleTheme = () => {
        setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
    };

    useEffect(() => {
        chrome.storage.local.get(['autoRefreshEnabled'], (result) => {
            if (typeof result.autoRefreshEnabled === 'boolean') {
                setAutoRefreshEnabled(result.autoRefreshEnabled);
            }
        });
    }, []);
      
    // 상태 변경 시 저장
    useEffect(() => {
        chrome.storage.local.set({ autoRefreshEnabled });
    }, [autoRefreshEnabled]);

    useEffect(() => {
        chrome.storage.local.get(['token'], (result) => {
            const token = result.token;
            setIsLoggedIn(!!token);
            setIsLoading(false)
            if (token) {
                const payload = parseJwt(token);
                setUserInfo(payload);
                } else {
                setUserInfo(null);
            }
        });

        function handleStorageChange(changes, area) {
            if (area === "local" && changes.token) {
                const newToken = changes.token.newValue;
                setIsLoggedIn(!!newToken);
                if (newToken) {
                    const payload = parseJwt(newToken);
                    setUserInfo(payload);
                    } else {
                    setUserInfo(null);
                }
            }
        }
        chrome.storage.onChanged.addListener(handleStorageChange);
        return () => {
            chrome.storage.onChanged.removeListener(handleStorageChange);
        };
    }, []);

    const detectPageMode = async () => {
        try {
            const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
            const currentTab = tabs[0];
            if (!currentTab?.url) return;
            const url = currentTab.url;
            const mode = getPageMode(url);

            setPageMode(PAGE_MODES[mode.toUpperCase()]);
        } catch (error) {
            console.error('페이지 모드 감지 실패:', error);
            setPageMode(PAGE_MODES.DEFAULT);
        }
    };

    useEffect(() => {
        detectPageMode();
        const handleTabUpdated = (tabId, changeInfo, tab) => {
            if (changeInfo.url) {
                setTimeout(detectPageMode, 100);
            }
        };
        const handleTabActivated = (activeInfo) => {
            setTimeout(detectPageMode, 100);
        };
        chrome.tabs.onUpdated.addListener(handleTabUpdated);
        chrome.tabs.onActivated.addListener(handleTabActivated);
        const handleSidePanelFocus = () => {
            detectPageMode();
        };
        window.addEventListener('focus', handleSidePanelFocus);
        return () => {
            chrome.tabs.onUpdated.removeListener(handleTabUpdated);
            chrome.tabs.onActivated.removeListener(handleTabActivated);
            window.removeEventListener('focus', handleSidePanelFocus);
        };
    }, []);

    //si
    useEffect(() => {
        if (autoRefreshEnabled) {
            setLastMode(pageMode);
        } else if (pageMode === PAGE_MODES.DEFAULT) {
            setLastMode(PAGE_MODES.DEFAULT);
        } else if (lastMode === PAGE_MODES.DEFAULT) {
            setLastMode(pageMode);
        }
    }, [pageMode, autoRefreshEnabled]);

    // AutoMode 토글 상태 background로 전달
    useEffect(() => {
        chrome.runtime.sendMessage({ type: "AUTO_REFRESH_ENABLED", value: autoRefreshEnabled });
    }, [autoRefreshEnabled]);


    // Footer 버튼 핸들러 관리
    const [recommendationFooterClick, setRecommendationFooterClick] = useState(() => () => {});

    // 페이지별 컴포넌트 렌더링
    const renderPage = () => {
        switch (pageMode) {
            case PAGE_MODES.DEFAULT:
                return <DefaultPage />;
            case PAGE_MODES.DOCUMENT:
                return <DocumentSummary />;
            case PAGE_MODES.YOUTUBE:
                return <YoutubeSummary />;
            case PAGE_MODES.RECOMMENDATION:
                return <Recommendation setFooterClick={setRecommendationFooterClick} />;
            case PAGE_MODES.SENSITIVE:
                return <SensitivePage />;
            default:
                return <DefaultPage />;
        }
    };


    // auto false용 페이지 렌더
    const renderPage2 = (mode) => {
        switch (mode) {
            case PAGE_MODES.DEFAULT:
                return <DefaultPage />;
            case PAGE_MODES.DOCUMENT:
                return <DocumentSummary />;
            case PAGE_MODES.YOUTUBE:
                return <YoutubeSummary />;
            case PAGE_MODES.RECOMMENDATION:
                return <Recommendation setFooterClick={setRecommendationFooterClick} />;
            case PAGE_MODES.SENSITIVE:
                return <SensitivePage />;
            default:
                return <DefaultPage />;
        }
    };


    if (isLoading) {
        return <LoadingSpinner />;
    }
    if (!isLoggedIn) {
        return <LoginPage theme={theme} setTheme={setTheme}/>;
    }

    let pageToRender = null;

    // 자동 갱신 비활성화 시에도 Default 페이지에 대한 감지(양방향)은 가능하도록
    if (autoRefreshEnabled) {
        pageToRender = renderPage(pageMode);
    } 
    else {
        if (pageMode === PAGE_MODES.DEFAULT) {
            pageToRender = renderPage2(PAGE_MODES.DEFAULT);
            // setState는 렌더 중 직접 호출 시 문제유발 가능. useEffect로 관리
            // setLastMode(PAGE_MODES.DEFAULT);
        }
        else if (lastMode === PAGE_MODES.DEFAULT) {
            pageToRender = renderPage2(pageMode);
            // setLastMode(pageMode); // 마찬가지
        }
        else {
            pageToRender = renderPage2(lastMode);
        }
    }

    return (
        <>
            <WebSocketProvider>
                <div className="app-container">
                    <Header theme={theme} toggleTheme={toggleTheme} userInfo={userInfo}/>
                    <div className="app-content">
                        {pageToRender}
                    </div>
                    {pageMode !== PAGE_MODES.DEFAULT && (
                        <Footer>
                            {pageMode === PAGE_MODES.RECOMMENDATION && (
                                <RecommendationFooterContent
                                onClick={recommendationFooterClick}
                                setLastMode={setLastMode}/>
                            )}
                            <AutoRefreshToggleButton enabled={autoRefreshEnabled}
                                onToggle={() => setAutoRefreshEnabled(e => !e)}/>
                        </Footer>
                    )}
                </div>
            </WebSocketProvider>
        </>
    );
}
