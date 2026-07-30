#!/usr/bin/env python3
import time
import os
import sys
import re
import logging
from datetime import datetime

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import CUPS_LOG_PATH
from app.database import SessionLocal, engine, Base
from app.models import User, PrintLog

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

Base.metadata.create_all(bind=engine)

def parse_cups_log_line(line: str):
    """
    Accurately parses CUPS page_log lines.
    Format: <printer> <user> <job_id> [<timestamp>] [total|page_num] <pages> <copies/billing> ... <job_title>
    """
    line = line.strip()
    if not line:
        return None
    parts = line.split()
    if len(parts) < 7:
        return None

    printer_name = parts[0]
    msnv = parts[1]

    printed_at = datetime.now()
    try:
        match_time = re.search(r'\[(\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2})', line)
        if match_time:
            printed_at = datetime.strptime(match_time.group(1), '%d/%b/%Y:%H:%M:%S')
    except Exception:
        pass

    page_count = 1
    copies = 1
    if parts[5] == 'total' and len(parts) >= 7 and parts[6].isdigit():
        page_count = int(parts[6])
    elif parts[5].isdigit():
        page_count = int(parts[5])
        if parts[6].isdigit():
            copies = int(parts[6])

    doc_tokens = []
    for token in parts[7:]:
        if token in ['-', '%H', '%m', 'one-sided', 'two-sided-long-edge', 'two-sided-short-edge'] or token.startswith('%'):
            continue
        doc_tokens.append(token)

    document_name = ' '.join(doc_tokens) if doc_tokens else 'Tài_Liệu_In.pdf'

    return {
        'msnv': msnv,
        'printer_name': printer_name,
        'document_name': document_name,
        'page_count': page_count,
        'copies': copies,
        'printed_at': printed_at
    }

def sync_all_cups_logs(db=None):
    """Syncs existing CUPS logs from log files to SQLite database."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    log_files = ['/var/log/cups/page_log.1', CUPS_LOG_PATH]
    added_count = 0

    try:
        for file_path in log_files:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        data = parse_cups_log_line(line)
                        if not data:
                            continue

                        # Ensure User exists
                        user = db.query(User).filter(User.msnv == data['msnv']).first()
                        if not user:
                            user = User(
                                msnv=data['msnv'],
                                fullname=f'Nhân viên {data["msnv"]}',
                                email=f'{data["msnv"]}@lta.com.vn',
                                department='Khối Văn Phòng',
                                role='admin' if data['msnv'] == 'admin' else 'user'
                            )
                            db.add(user)
                            db.commit()

                        # Prevent duplicate logs
                        exists = db.query(PrintLog).filter(
                            PrintLog.msnv == data['msnv'],
                            PrintLog.printer_name == data['printer_name'],
                            PrintLog.document_name == data['document_name'],
                            PrintLog.printed_at == data['printed_at']
                        ).first()

                        if not exists:
                            log_entry = PrintLog(
                                msnv=data['msnv'],
                                printer_name=data['printer_name'],
                                document_name=data['document_name'],
                                page_count=data['page_count'],
                                copies=data['copies'],
                                printed_at=data['printed_at']
                            )
                            db.add(log_entry)
                            added_count += 1

        db.commit()
        if added_count > 0:
            logging.info(f"Successfully synced {added_count} print log entries from CUPS page_log.")
    except Exception as e:
        logging.error(f"Error syncing CUPS logs: {e}")
        db.rollback()
    finally:
        if close_db:
            db.close()

def monitor_cups_log():
    """Continuously monitors CUPS page_log for new print jobs."""
    sync_all_cups_logs()
    
    if not os.path.exists(CUPS_LOG_PATH):
        logging.warning(f"File {CUPS_LOG_PATH} does not exist yet. Waiting...")
        while not os.path.exists(CUPS_LOG_PATH):
            time.sleep(5)

    with open(CUPS_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
        f.seek(0, os.SEEK_END)
        logging.info("CUPS log monitor active. Listening for real-time print jobs...")

        db = SessionLocal()
        try:
            while True:
                line = f.readline()
                if not line:
                    time.sleep(1)
                    continue

                data = parse_cups_log_line(line)
                if data:
                    try:
                        user = db.query(User).filter(User.msnv == data['msnv']).first()
                        if not user:
                            user = User(
                                msnv=data['msnv'],
                                fullname=f'Nhân viên {data["msnv"]}',
                                email=f'{data["msnv"]}@lta.com.vn',
                                department='Khối Văn Phòng',
                                role='admin' if data['msnv'] == 'admin' else 'user'
                            )
                            db.add(user)
                            db.commit()

                        log_entry = PrintLog(
                            msnv=data['msnv'],
                            printer_name=data['printer_name'],
                            document_name=data['document_name'],
                            page_count=data['page_count'],
                            copies=data['copies'],
                            printed_at=data['printed_at']
                        )
                        db.add(log_entry)
                        db.commit()
                        logging.info(f"Logged print job: User {data['msnv']} printed '{data['document_name']}' ({data['page_count']} pages) on {data['printer_name']}")
                    except Exception as err:
                        logging.error(f"Error saving log line '{line.strip()}': {err}")
                        db.rollback()
        finally:
            db.close()

if __name__ == "__main__":
    try:
        monitor_cups_log()
    except KeyboardInterrupt:
        logging.info("CUPS log monitor stopped.")
