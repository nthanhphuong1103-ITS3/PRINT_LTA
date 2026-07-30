// ===== LTA Print Guard - Background Service Worker =====
// Xử lý kiểm tra auth và điều hướng tab

const LTA_CHECK_URL = 'http://localhost:8000/api/auth/check';
const LTA_LOGIN_URL = 'http://localhost:8000/login';
const LTA_DASHBOARD_URL = 'http://localhost:8000/dashboard';

// ===== Lắng nghe messages từ content script =====
chrome.runtime.onMessage.addListener(async (msg, sender, sendResponse) => {

    if (msg.action === 'CTRL_P_PRESSED') {
        await handleCtrlP(sender.tab);
    }

    if (msg.action === 'OPEN_LTA_PRINT') {
        await openOrFocusLtaTab(LTA_DASHBOARD_URL);
    }

    if (msg.action === 'OPEN_LTA_LOGIN') {
        await openOrFocusLtaTab(LTA_LOGIN_URL);
    }
});

// ===== Xử lý Ctrl+P =====
async function handleCtrlP(sourceTab) {
    try {
        // Kiểm tra trạng thái đăng nhập từ server
        const response = await fetch(LTA_CHECK_URL, {
            method: 'GET',
            credentials: 'include'
        });

        if (!response.ok) {
            // Server không phản hồi → Mở trang đăng nhập
            await openOrFocusLtaTab(LTA_LOGIN_URL);
            return;
        }

        const data = await response.json();

        // Gửi kết quả về content script để hiện overlay
        if (sourceTab?.id) {
            chrome.tabs.sendMessage(sourceTab.id, {
                action: 'SHOW_LTA_OVERLAY',
                loggedIn: data.logged_in,
                userInfo: data.logged_in ? { msnv: data.msnv, fullname: data.fullname } : null
            });
        }

    } catch (error) {
        // Không thể kết nối đến server LTA Print
        console.warn('[LTA Print Guard] Không thể kết nối server:', error);

        // Mở tab LTA Print để người dùng đăng nhập
        await openOrFocusLtaTab(LTA_LOGIN_URL);
    }
}

// ===== Mở hoặc focus tab LTA Print =====
async function openOrFocusLtaTab(url) {
    // Tìm tab LTA Print đang mở
    const tabs = await chrome.tabs.query({ url: 'http://localhost:8000/*' });

    if (tabs.length > 0) {
        // Focus vào tab đã có
        const ltaTab = tabs[0];
        await chrome.tabs.update(ltaTab.id, { active: true, url: url });
        await chrome.windows.update(ltaTab.windowId, { focused: true });
    } else {
        // Mở tab mới
        await chrome.tabs.create({ url: url, active: true });
    }
}
