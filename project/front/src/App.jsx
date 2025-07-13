import { useState, useEffect, useCallback } from "react";
import Header from './components/ui/Header';
import Footer from './components/ui/Footer';
import LoginPage from './components/pages/LoginPage';
import DefaultPage from './components/pages/DefaultPage';
import DocumentSummary from './components/pages/DocumentSummary';
import YoutubeSummary from './components/pages/YoutubeSummary';
import Recommendation, { RecommendationFooterContent } from './components/pages/Recommendation';
import SensitivePage from './components/pages/SensitivePage';
import LoadingSpinner from './components/ui/LoadingSpinner';
import { parseJwt } from './utils/jwtUtils';
import { PAGE_MODES } from './utils/constants';
import { WebSocketProvider } from "./utils/websocketProvider";
import "./App.css";

export default function App() {
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [userInfo, setUserInfo] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [pageMode, setPageMode] = useState(PAGE_MODES.DEFAULT);
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
            if (url.includes('login') || url.includes('signup') || url.includes('signin') || 
                url.includes('auth') || url.includes('password') || url.includes('account')) {
                setPageMode(PAGE_MODES.SENSITIVE);
                return;
            }
            if (url.startsWith('chrome://') || url.startsWith('chrome-extension://') || 
                url.startsWith('about:') || url.startsWith('moz-extension://')) {
                setPageMode(PAGE_MODES.DEFAULT);
                return;
            }
            if (url === 'https://www.google.com' || url === 'https://www.naver.com' ||
                url === 'https://www.youtube.com') {
                setPageMode(PAGE_MODES.DEFAULT);
                return;
            }
            if (url.includes('.pdf') || url.includes('.doc') || url.includes('.docx')) {
                setPageMode(PAGE_MODES.DOCUMENT);
                return;
            }
            if (url.includes('youtube.com/watch') || url.includes('youtube.com/shorts')) {
                setPageMode(PAGE_MODES.YOUTUBE);
                return;
            }
            setPageMode(PAGE_MODES.RECOMMENDATION);
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

    if (isLoading) {
        return <LoadingSpinner />;
    }
    if (!isLoggedIn) {
        return <LoginPage theme={theme} setTheme={setTheme}/>;
    }

    return (
        <>
            <WebSocketProvider>
                <div className="app-container">
                    <Header theme={theme} toggleTheme={toggleTheme} userInfo={userInfo}/>
                    <div className="app-content">
                        {renderPage()}
                    </div>
                    <Footer>
                        {pageMode === PAGE_MODES.RECOMMENDATION && (
                            <RecommendationFooterContent onClick={recommendationFooterClick} />
                        )}
                    </Footer>
                </div>
            </WebSocketProvider>
        </>
    );
}
