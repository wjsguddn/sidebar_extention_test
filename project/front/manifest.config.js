// manifest.config.js
export default {
  // ── 기본 메타 ─────────────────────────────────────
  manifest_version: 3,
  name: 'My React Extension',          // 확장 이름
  description: 'React + Vite + MV3',
  version: '0.0.1',

  icons: {
    '16': 'icons/16.png',
    '48': 'icons/48.png',
    '128': 'icons/128.png'
  },

  // ── 사이드패널 기본 경로 ────────────────────
  side_panel: {
    default_path: 'index.html'
  },


  // ── 액션(툴바 아이콘) ───────────────────────
  action: {
    default_title: 'Open Side Panel',
    default_icon: {
      '128': 'icons/128.png'
    }
  },

  // ── 백그라운드(서비스 워커) ─────────────────────
  background: {
    service_worker: 'src/background.js',   // src/background.js → 빌드 결과
    type: 'module'
  },

  // ── 권한 ───────────────────────────────────────
  permissions: [
    'tabs',
    'sidePanel',
    'scripting'
  ],
  host_permissions: ['<all_urls>']

}