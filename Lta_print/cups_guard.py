#!/usr/bin/env python3
"""
LTA Print Guard - CUPS Job Monitor
Theo dõi hàng đợi CUPS, khi phát hiện job từ chối/bị giữ lại do chưa đăng nhập
→ Hiển thị thông báo desktop yêu cầu đăng nhập
"""
import subprocess
import time
import os
import sys
import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

LTA_CHECK_URL = "http://localhost:8000/api/auth/check"
LTA_LOGIN_URL = "http://localhost:8000/login"
POLL_INTERVAL = 1  # giây
DISPLAY = ":0"     # X11 display mặc định

# CUPS error_log thường ở đây
CUPS_ERROR_LOG = "/var/log/cups/error_log"


def check_lta_logged_in() -> bool:
    """Kiểm tra xem có ai đang đăng nhập LTA Print không."""
    try:
        r = requests.get(LTA_CHECK_URL, timeout=2)
        return r.json().get("logged_in", False)
    except Exception:
        return False


def get_held_jobs() -> list:
    """Lấy danh sách các print job đang bị hold/stopped trong CUPS."""
    try:
        result = subprocess.run(
            ["lpstat", "-o"],
            capture_output=True, text=True, timeout=5
        )
        jobs = []
        for line in result.stdout.splitlines():
            # Job bị hold: "printer-job_id      user   size   date time"
            # Stopped/held jobs thường có từ khóa "held"
            if line.strip():
                jobs.append(line.strip())
        return jobs
    except Exception:
        return []


def get_all_jobs_status() -> list:
    """Lấy trạng thái chi tiết các jobs bằng lpstat -l."""
    try:
        result = subprocess.run(
            ["lpstat", "-W", "not-completed", "-l"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout
    except Exception:
        return ""


def show_desktop_notification(title: str, message: str, urgency: str = "critical"):
    """
    Hiển thị thông báo desktop bằng notify-send.
    urgency: low | normal | critical
    """
    env = os.environ.copy()
    env["DISPLAY"] = DISPLAY
    env["DBUS_SESSION_BUS_ADDRESS"] = get_dbus_address()

    try:
        subprocess.run(
            [
                "notify-send",
                "--urgency=" + urgency,
                "--expire-time=15000",   # 15 giây
                "--icon=printer",
                title,
                message
            ],
            env=env,
            timeout=5
        )
        logging.info(f"[Notification] {title}: {message}")
    except Exception as e:
        logging.warning(f"notify-send failed: {e}")
        # Fallback: dùng zenity nếu có
        try:
            subprocess.Popen(
                ["zenity", "--warning", "--title", title, "--text", message, "--timeout=15"],
                env=env
            )
        except Exception:
            pass


def get_dbus_address() -> str:
    """Lấy DBUS_SESSION_BUS_ADDRESS của phiên desktop đang chạy."""
    try:
        result = subprocess.run(
            ["grep", "-r", "DBUS_SESSION_BUS_ADDRESS", "/proc"],
            capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.splitlines():
            if "DBUS_SESSION_BUS_ADDRESS" in line:
                parts = line.split("DBUS_SESSION_BUS_ADDRESS=")
                if len(parts) > 1:
                    return parts[1].split("\x00")[0].strip()
    except Exception:
        pass

    # Thử các đường dẫn mặc định
    for uid in ["1000", "1001"]:
        path = f"/run/user/{uid}/bus"
        if os.path.exists(path):
            return f"unix:path={path}"
    return "unix:path=/run/user/1000/bus"


def open_login_browser():
    """Mở trình duyệt đến trang đăng nhập LTA Print."""
    env = os.environ.copy()
    env["DISPLAY"] = DISPLAY
    env["DBUS_SESSION_BUS_ADDRESS"] = get_dbus_address()
    try:
        subprocess.Popen(
            ["xdg-open", LTA_LOGIN_URL],
            env=env
        )
        logging.info(f"Opened browser to {LTA_LOGIN_URL}")
    except Exception as e:
        logging.warning(f"Failed to open browser: {e}")


def get_pending_jobs_count() -> int:
    """Đếm số lượng jobs đang chờ/bị hold."""
    try:
        result = subprocess.run(
            ["lpstat", "-o"],
            capture_output=True, text=True, timeout=5
        )
        return len([l for l in result.stdout.splitlines() if l.strip()])
    except Exception:
        return 0


def monitor_cups_jobs():
    """
    Vòng lặp chính: Theo dõi CUPS jobs.
    Nếu có job mới và chưa đăng nhập LTA Print → hiện thông báo + mở trình duyệt.
    """
    logging.info("LTA Print Guard - CUPS Job Monitor started")
    logging.info(f"Checking auth at: {LTA_CHECK_URL}")

    last_job_count = get_pending_jobs_count()
    notified = False
    notification_cooldown = 0  # tránh spam thông báo

    while True:
        try:
            current_job_count = get_pending_jobs_count()

            # Phát hiện có job mới được submit
            if current_job_count > last_job_count:
                new_jobs = current_job_count - last_job_count
                logging.info(f"Detected {new_jobs} new print job(s)!")

                # Kiểm tra đăng nhập LTA Print
                logged_in = check_lta_logged_in()

                if not logged_in and notification_cooldown <= 0:
                    logging.warning("User NOT logged in! Showing notification...")

                    show_desktop_notification(
                        "🖨️ LTA Print - Yêu cầu đăng nhập",
                        "Bạn chưa đăng nhập hệ thống quản lý in ấn.\n"
                        "Vui lòng đăng nhập tại:\n"
                        "http://localhost:8000/login"
                    )

                    # Mở trình duyệt đến trang đăng nhập
                    open_login_browser()

                    notification_cooldown = 30  # chờ 30s trước khi thông báo lần tiếp
                elif logged_in:
                    logging.info("User is logged in. Print job allowed.")

            last_job_count = current_job_count

            # Đếm ngược cooldown
            if notification_cooldown > 0:
                notification_cooldown -= POLL_INTERVAL

        except Exception as e:
            logging.error(f"Monitor error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        monitor_cups_jobs()
    except KeyboardInterrupt:
        logging.info("LTA Print Guard CUPS monitor stopped.")
