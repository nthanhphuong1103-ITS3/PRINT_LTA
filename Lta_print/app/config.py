import os
from dotenv import load_dotenv

# Tự động nạp file .env vào biến môi trường hệ thống
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'lta_print.db')}"

SECRET_KEY = os.getenv("SECRET_KEY", "lta-print-super-secret-key-2026")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Lta@19000271#")
CUPS_LOG_PATH = os.getenv("CUPS_LOG_PATH", "/var/log/cups/page_log")
DEFAULT_USER_QUOTA = 500
SESSION_COOKIE_NAME = "lta_session"
