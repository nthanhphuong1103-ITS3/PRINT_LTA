// ===== LTA Print Guard - Popup Script =====
const LTA_CHECK_URL = 'http://localhost:8000/api/auth/check';
const LTA_LOGIN_URL = 'http://localhost:8000/login';
const LTA_DASHBOARD_URL = 'http://localhost:8000/dashboard';

async function checkStatus() {
    const serverEl = document.getElementById('server-status');
    const authEl = document.getElementById('auth-status');

    try {
        const res = await fetch(LTA_CHECK_URL, { credentials: 'include' });
        if (!res.ok) throw new Error('Server lỗi');

        const data = await res.json();

        // Server online
        serverEl.innerHTML = '<span class="dot dot-green"></span><span class="status-online">Đang hoạt động</span>';

        if (data.logged_in) {
            authEl.innerHTML = `<span class="dot dot-indigo"></span><span class="status-logged-in">Đã đăng nhập (${data.msnv})</span>`;
            document.getElementById('login-btn').textContent = '🚪 Đăng xuất';
        } else {
            authEl.innerHTML = '<span class="dot dot-amber"></span><span class="status-logged-out">Chưa đăng nhập</span>';
            document.getElementById('login-btn').textContent = '🔑 Đăng nhập';
        }
    } catch (e) {
        serverEl.innerHTML = '<span class="dot dot-red"></span><span class="status-offline">Không kết nối được</span>';
        authEl.innerHTML = '<span class="dot dot-red"></span><span class="status-offline">Không xác định</span>';
    }
}

async function openOrFocusLta(url) {
    const tabs = await chrome.tabs.query({ url: 'http://localhost:8000/*' });
    if (tabs.length > 0) {
        await chrome.tabs.update(tabs[0].id, { active: true, url: url });
        await chrome.windows.update(tabs[0].windowId, { focused: true });
    } else {
        await chrome.tabs.create({ url: url });
    }
    window.close();
}

document.getElementById('open-btn').addEventListener('click', () => openOrFocusLta(LTA_DASHBOARD_URL));
document.getElementById('login-btn').addEventListener('click', () => openOrFocusLta(LTA_LOGIN_URL));

// Kiểm tra trạng thái khi mở popup
checkStatus();
