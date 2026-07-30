// ===== LTA Print Guard - Content Script (v2) =====
// Bắt Ctrl+P trên TẤT CẢ trang, fetch auth TRỰC TIẾP, hiện overlay ngay

const LTA_CHECK_URL = 'http://localhost:8000/api/auth/check';
const LTA_LOGIN_URL = 'http://localhost:8000/login';
const LTA_DASHBOARD_URL = 'http://localhost:8000/dashboard';

// ===== Ghi đè window.print để bắt cả lệnh in từ web app =====
const _originalPrint = window.print.bind(window);
window.print = function () {
    handlePrintAttempt();
};

// ===== Bắt phím Ctrl+P - capture phase ưu tiên cao nhất =====
document.addEventListener('keydown', function (e) {
    const isCtrlP = (e.ctrlKey || e.metaKey) && (e.key === 'p' || e.key === 'P');
    if (!isCtrlP) return;

    e.preventDefault();
    e.stopImmediatePropagation();
    e.stopPropagation();

    handlePrintAttempt();
}, true);

// ===== Bắt sự kiện beforeprint (dự phòng) =====
window.addEventListener('beforeprint', function (e) {
    // Hiện overlay cảnh báo (không thể cancel event này nhưng cảnh báo được)
    handlePrintAttempt();
}, true);

// ===== Xử lý khi người dùng cố in =====
async function handlePrintAttempt() {
    // Tránh hiện overlay trùng
    if (document.getElementById('lta-print-overlay')) return;

    // Hiện overlay loading ngay lập tức
    showLoadingOverlay();

    try {
        const response = await fetch(LTA_CHECK_URL, {
            method: 'GET',
            credentials: 'include',
            cache: 'no-store'
        });

        // Xóa overlay loading
        removeOverlay();

        if (!response.ok) {
            // Server lỗi → coi như chưa đăng nhập
            showLoginRequired();
            return;
        }

        const data = await response.json();

        if (data.logged_in) {
            showLoggedInOverlay(data);
        } else {
            showLoginRequired();
        }

    } catch (err) {
        // Không kết nối được server LTA Print
        removeOverlay();
        showServerOffline();
    }
}

// ===== Overlay: Đang kiểm tra =====
function showLoadingOverlay() {
    const overlay = createOverlay();
    overlay.innerHTML = `
        <div id="lta-card" style="
            background:#0f172a;border:1px solid #334155;border-radius:20px;
            padding:32px;max-width:360px;width:90%;text-align:center;
            box-shadow:0 25px 60px rgba(0,0,0,0.6);
            animation: ltaSlide 0.2s ease;
        ">
            <style>
                @keyframes ltaFade{from{opacity:0}to{opacity:1}}
                @keyframes ltaSlide{from{transform:translateY(16px);opacity:0}to{transform:translateY(0);opacity:1}}
                @keyframes ltaSpin{to{transform:rotate(360deg)}}
                #lta-spinner{animation:ltaSpin 0.8s linear infinite;display:inline-block;}
            </style>
            <div id="lta-spinner" style="font-size:36px;margin-bottom:16px;">⟳</div>
            <p style="color:#94a3b8;font-size:13px;margin:0;">Đang kiểm tra hệ thống LTA Print...</p>
        </div>
    `;
    document.body.appendChild(overlay);
}

// ===== Overlay: Chưa đăng nhập =====
function showLoginRequired() {
    const overlay = createOverlay();
    overlay.innerHTML = `
        <div id="lta-card" style="
            background:#0f172a;border:1px solid rgba(239,68,68,0.35);border-radius:20px;
            padding:36px 32px;max-width:420px;width:90%;text-align:center;
            box-shadow:0 25px 60px rgba(0,0,0,0.6),0 0 40px rgba(220,38,38,0.08);
            animation:ltaSlide 0.25s ease;
        ">
            <style>
                @keyframes ltaFade{from{opacity:0}to{opacity:1}}
                @keyframes ltaSlide{from{transform:translateY(16px);opacity:0}to{transform:translateY(0);opacity:1}}
                @keyframes ltaPulse{0%,100%{box-shadow:0 0 0 0 rgba(220,38,38,0.4)}50%{box-shadow:0 0 0 10px rgba(220,38,38,0)}}
            </style>
            <div style="
                width:64px;height:64px;
                background:linear-gradient(135deg,#dc2626,#ea580c);
                border-radius:18px;display:flex;align-items:center;justify-content:center;
                margin:0 auto 20px;font-size:28px;
                animation:ltaPulse 2s infinite;
            ">🔒</div>
            <h2 style="color:#fff;font-size:19px;font-weight:800;margin:0 0 8px;letter-spacing:-0.3px;">
                Yêu cầu đăng nhập
            </h2>
            <p style="color:#94a3b8;font-size:13px;margin:0 0 4px;">Bạn chưa đăng nhập vào hệ thống</p>
            <p style="color:#f87171;font-size:14px;font-weight:700;margin:0 0 10px;">LTA Print</p>
            <p style="color:#475569;font-size:11px;margin:0 0 24px;line-height:1.6;">
                Lệnh in đã bị chặn.<br>Vui lòng đăng nhập để sử dụng máy in.
            </p>
            <div style="display:flex;gap:10px;justify-content:center;">
                <button id="lta-login-btn" style="
                    background:linear-gradient(135deg,#dc2626,#ea580c);
                    color:#fff;border:none;padding:12px 28px;border-radius:11px;
                    font-size:13px;font-weight:700;cursor:pointer;
                    box-shadow:0 4px 20px rgba(220,38,38,0.35);
                    transition:all 0.15s;
                " onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform=''">
                    🔑 Đăng nhập ngay
                </button>
                <button id="lta-close-btn" style="
                    background:#1e293b;color:#64748b;border:1px solid #334155;
                    padding:12px 18px;border-radius:11px;font-size:13px;cursor:pointer;
                    transition:all 0.15s;
                " onmouseover="this.style.background='#334155'" onmouseout="this.style.background='#1e293b'">
                    Đóng
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    setupOverlayButtons(overlay, false);
}

// ===== Overlay: Đã đăng nhập =====
function showLoggedInOverlay(data) {
    const overlay = createOverlay();
    overlay.innerHTML = `
        <div id="lta-card" style="
            background:#0f172a;border:1px solid rgba(99,102,241,0.3);border-radius:20px;
            padding:36px 32px;max-width:400px;width:90%;text-align:center;
            box-shadow:0 25px 60px rgba(0,0,0,0.6),0 0 40px rgba(99,102,241,0.06);
            animation:ltaSlide 0.25s ease;
        ">
            <style>
                @keyframes ltaSlide{from{transform:translateY(16px);opacity:0}to{transform:translateY(0);opacity:1}}
            </style>
            <div style="
                width:64px;height:64px;
                background:linear-gradient(135deg,#4f46e5,#2563eb);
                border-radius:18px;display:flex;align-items:center;justify-content:center;
                margin:0 auto 20px;font-size:28px;
            ">🖨️</div>
            <h2 style="color:#fff;font-size:19px;font-weight:800;margin:0 0 8px;">LTA Print</h2>
            <p style="color:#94a3b8;font-size:13px;margin:0 0 6px;">
                Xin chào, <strong style="color:#818cf8">${data.fullname || data.msnv}</strong>
            </p>
            <p style="color:#475569;font-size:11px;margin:0 0 24px;">
                Bạn đã đăng nhập. Mở trang quản lý in?
            </p>
            <div style="display:flex;gap:10px;justify-content:center;">
                <button id="lta-go-btn" style="
                    background:linear-gradient(135deg,#4f46e5,#2563eb);
                    color:#fff;border:none;padding:12px 24px;border-radius:11px;
                    font-size:13px;font-weight:600;cursor:pointer;
                    box-shadow:0 4px 20px rgba(79,70,229,0.35);
                    transition:all 0.15s;
                " onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform=''">
                    Mở LTA Print →
                </button>
                <button id="lta-close-btn" style="
                    background:#1e293b;color:#64748b;border:1px solid #334155;
                    padding:12px 18px;border-radius:11px;font-size:13px;cursor:pointer;
                    transition:all 0.15s;
                " onmouseover="this.style.background='#334155'" onmouseout="this.style.background='#1e293b'">
                    Đóng
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    setupOverlayButtons(overlay, true);
}

// ===== Overlay: Server offline =====
function showServerOffline() {
    const overlay = createOverlay();
    overlay.innerHTML = `
        <div id="lta-card" style="
            background:#0f172a;border:1px solid rgba(245,158,11,0.3);border-radius:20px;
            padding:32px;max-width:380px;width:90%;text-align:center;
            box-shadow:0 25px 60px rgba(0,0,0,0.6);animation:ltaSlide 0.25s ease;
        ">
            <style>@keyframes ltaSlide{from{transform:translateY(16px);opacity:0}to{transform:translateY(0);opacity:1}}</style>
            <div style="width:60px;height:60px;background:linear-gradient(135deg,#d97706,#f59e0b);border-radius:16px;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:26px;">⚠️</div>
            <h2 style="color:#fff;font-size:17px;font-weight:700;margin:0 0 8px;">Không kết nối được</h2>
            <p style="color:#94a3b8;font-size:12px;margin:0 0 8px;">Server LTA Print chưa khởi động</p>
            <p style="color:#64748b;font-size:11px;margin:0 0 20px;">Hãy đảm bảo server đang chạy tại<br><code style="color:#f59e0b">localhost:8000</code></p>
            <button id="lta-close-btn" style="
                background:#1e293b;color:#94a3b8;border:1px solid #334155;
                padding:10px 24px;border-radius:10px;font-size:13px;cursor:pointer;
            ">Đóng</button>
        </div>
    `;
    document.body.appendChild(overlay);
    setupOverlayButtons(overlay, false);
}

// ===== Helper: Tạo overlay container =====
function createOverlay() {
    removeOverlay();
    const overlay = document.createElement('div');
    overlay.id = 'lta-print-overlay';
    overlay.style.cssText = `
        position:fixed;top:0;left:0;right:0;bottom:0;
        background:rgba(0,0,0,0.8);backdrop-filter:blur(10px);
        z-index:2147483647;display:flex;align-items:center;justify-content:center;
        font-family:'Segoe UI',system-ui,sans-serif;
    `;
    // Click nền để đóng
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) removeOverlay();
    });
    return overlay;
}

// ===== Helper: Gắn sự kiện các nút =====
function setupOverlayButtons(overlay, isLoggedIn) {
    document.getElementById('lta-close-btn')?.addEventListener('click', removeOverlay);

    if (isLoggedIn) {
        document.getElementById('lta-go-btn')?.addEventListener('click', () => {
            chrome.runtime.sendMessage({ action: 'OPEN_LTA_PRINT' });
            removeOverlay();
        });
    } else {
        document.getElementById('lta-login-btn')?.addEventListener('click', () => {
            chrome.runtime.sendMessage({ action: 'OPEN_LTA_LOGIN' });
            removeOverlay();
        });
    }

    // ESC để đóng
    const escHandler = (e) => {
        if (e.key === 'Escape') { removeOverlay(); document.removeEventListener('keydown', escHandler); }
    };
    document.addEventListener('keydown', escHandler);
}

// ===== Helper: Xóa overlay =====
function removeOverlay() {
    document.getElementById('lta-print-overlay')?.remove();
}
