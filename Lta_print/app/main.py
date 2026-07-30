from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, Response
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
import csv
import io
import os
from datetime import datetime

import threading
from .database import engine, get_db, Base
from .models import User, PrintLog
from .printer import enable_printers, disable_printers, get_printer_status, get_system_idle_seconds
from .auth import get_current_user_from_session, require_admin
from .config import ADMIN_USERNAME, ADMIN_PASSWORD
from print_monitor import sync_all_cups_logs, monitor_cups_log

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="LTA Print Management System")

@app.on_event("startup")
def startup_event():
    sync_all_cups_logs()
    # Thread 1: Monitor CUPS page_log để ghi lịch sử in
    t = threading.Thread(target=monitor_cups_log, daemon=True)
    t.start()
    # Thread 2: CUPS Guard - phát hiện job mới và yêu cầu đăng nhập
    try:
        import importlib.util, os as _os
        guard_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "cups_guard.py")
        if _os.path.exists(guard_path):
            import subprocess as _sp
            import sys as _sys
            _env = _os.environ.copy()
            _env.setdefault("DISPLAY", ":0")
            _env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{_os.getuid()}/bus")
            guard_proc = _sp.Popen([_sys.executable, guard_path], env=_env)
    except Exception as _e:
        import logging as _log
        _log.warning(f"Could not start cups_guard: {_e}")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


# Seed initial admin & sample data if database is brand new
def seed_initial_data():
    db = next(get_db())
    
    # Check or create dedicated Admin account
    admin_user = db.query(User).filter(User.msnv == ADMIN_USERNAME).first()
    if not admin_user:
        admin_user = User(
            msnv=ADMIN_USERNAME,
            fullname="Quản Trị Viên (System Admin)",
            email=f"{ADMIN_USERNAME}@lta.com.vn",
            department="Ban Quản Trị",
            role="admin",
            password=ADMIN_PASSWORD,
            page_quota=9999,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
    else:
        # Ensure credentials match requested admin settings
        admin_user.role = "admin"
        admin_user.password = ADMIN_PASSWORD
        db.commit()

    # Default employee demo user
    user_a = db.query(User).filter(User.msnv == "4642").first()
    if not user_a:
        user_a = User(
            msnv="4642",
            fullname="Nguyen Van A",
            email="a.nguyen@lta.com.vn",
            department="IT Team",
            role="user",  # Regular user
            page_quota=500,
            is_active=True
        )
        db.add(user_a)
        db.commit()
    else:
        user_a.role = "user"  # Reset demo user to regular user
        db.commit()

    user_b = db.query(User).filter(User.msnv == "1088").first()
    if not user_b:
        user_b = User(
            msnv="1088",
            fullname="Tran Thi B",
            email="b.tran@lta.com.vn",
            department="Kế Toán",
            role="user",
            page_quota=300,
            is_active=True
        )
        db.add(user_b)
        db.commit()

    # Seed sample print logs if empty
    if db.query(PrintLog).count() == 0:
        log1 = PrintLog(
            msnv="4642",
            printer_name="RICOH_MP2555",
            document_name="Bao_Cao_Tai_Chinh_Q2.pdf",
            page_count=24,
            copies=1,
            file_type="PDF"
        )
        log2 = PrintLog(
            msnv="1088",
            printer_name="HP_LaserJet_P2035",
            document_name="Hop_Dong_Lao_Dong_2026.docx",
            page_count=5,
            copies=2,
            file_type="DOCX"
        )
        db.add_all([log1, log2])
        db.commit()

seed_initial_data()

# ==================== CUPS CONTROLLER API ====================
@app.post("/api/printer/enable")
def api_enable_printers():
    res = enable_printers()
    return {"status": "success", "message": "Đã mở khóa máy in", "detail": res}

@app.post("/api/printer/disable")
def api_disable_printers():
    res = disable_printers()
    return {"status": "success", "message": "Đã khóa hệ thống máy in", "detail": res}

@app.get("/api/printer/status")
def api_printer_status():
    printers = get_printer_status()
    return {"printers": printers}

@app.get("/api/system/idle")
def api_system_idle():
    idle_sec = get_system_idle_seconds()
    return {"idle_seconds": idle_sec}

@app.post("/api/printer/simulate_print")
def simulate_print(
    request: Request,
    doc_name: str = Form(...),
    pages: int = Form(1),
    db: Session = Depends(get_db)
):
    current_user = get_current_user_from_session(request, db)
    printers = get_printer_status()
    
    # Check if any printer is unlocked / ready
    ready_printer = next((p for p in printers if p['status'] == 'Ready'), None)
    if not ready_printer:
        return {
            "status": "held",
            "message": "🔒 LỆNH IN BỊ GIỮ LẠI (Hold Queue)! Bạn cần ở phiên đăng nhập mở khóa mới có thể in.",
            "detail": "Printers are currently Disabled (Locked) or Offline."
        }
        
    # Create print log
    new_log = PrintLog(
        msnv=current_user.msnv,
        printer_name=ready_printer['name'],
        document_name=doc_name,
        page_count=pages,
        copies=1,
        file_type="PDF"
    )
    db.add(new_log)
    db.commit()
    return {
        "status": "printed",
        "message": f"✅ Đã nhả lệnh in '{doc_name}' ({pages} trang) thành công trên máy in {ready_printer['name']}!",
        "printer": ready_printer['name']
    }


# ==================== AUTH API ====================
@app.post("/api/auth/login")
def login(response: Response, msnv: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.msnv == msnv).first()
    if not user:
        # Create user dynamically on first SSO login
        user = User(
            msnv=msnv,
            fullname=f"Nhân viên {msnv}",
            email=f"{msnv}@lta.com.vn",
            department="Khối Văn Phòng",
            role="user",
            page_quota=500
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Tài khoản của bạn đã bị khóa")

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="msnv", value=user.msnv, httponly=True)
    return response

@app.post("/api/auth/loginadmin")
def login_admin(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    admin_user = db.query(User).filter(User.msnv == username, User.role == "admin").first()
    if admin_user and (admin_user.password == password or (username == ADMIN_USERNAME and password == ADMIN_PASSWORD)):
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(key="msnv", value=admin_user.msnv, httponly=True)
        return response
    
    return templates.TemplateResponse(
        request=request, 
        name="login_admin.html", 
        context={"error": "Tên tài khoản hoặc mật khẩu Admin không chính xác!"}
    )

@app.get("/api/auth/check")
def check_auth(request: Request, db: Session = Depends(get_db)):
    """Kiểm tra trạng thái đăng nhập - dùng cho Browser Extension"""
    from fastapi.responses import JSONResponse

    # Lấy origin từ request (extension gửi), nếu không có thì dùng wildcard
    origin = request.headers.get("origin") or request.headers.get("referer", "*")
    if origin and origin != "*":
        # Chỉ lấy phần scheme+host từ referer
        from urllib.parse import urlparse
        parsed = urlparse(origin)
        origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else origin

    cors_headers = {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET",
        "Access-Control-Allow-Headers": "Content-Type",
    }

    msnv = request.cookies.get("msnv")
    if not msnv:
        return JSONResponse(content={"logged_in": False}, headers=cors_headers)

    user = db.query(User).filter(User.msnv == msnv).first()
    if not user or not user.is_active:
        return JSONResponse(content={"logged_in": False}, headers=cors_headers)

    return JSONResponse(
        content={"logged_in": True, "msnv": user.msnv, "fullname": user.fullname},
        headers=cors_headers
    )


@app.get("/api/auth/logout")
def logout():
    disable_printers()  # Always lock printers on logout!
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="msnv")
    return response



# ==================== ADMIN & EXPORT API ====================
@app.get("/api/admin/export/logs")
def export_print_logs(msnv: str = None, db: Session = Depends(get_db)):
    """Xuất file CSV/Excel chi tiết lệnh in (Tổng hợp hoặc theo User)"""
    query = db.query(PrintLog)
    if msnv:
        query = query.filter(PrintLog.msnv == msnv)

    logs = query.order_by(PrintLog.printed_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'MSNV', 'Máy In', 'Tài Liệu', 'Số Trang', 'Số Bản In', 'Thời Gian'])

    for log in logs:
        writer.writerow([
            log.id, 
            log.msnv, 
            log.printer_name, 
            log.document_name, 
            log.page_count, 
            log.copies, 
            log.printed_at.strftime("%Y-%m-%d %H:%M:%S")
        ])

    output.seek(0)
    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    filename = f"Print_Report_{msnv if msnv else 'ALL'}_{datetime.now().strftime('%Y%m%d')}.csv"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response

@app.post("/api/admin/users/quota")
def update_user_quota(msnv: str = Form(...), page_quota: int = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.msnv == msnv).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    user.page_quota = page_quota
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/api/admin/users/toggle")
def toggle_user_active(msnv: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.msnv == msnv).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    user.is_active = not user.is_active
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

# ==================== VIEWS ====================
@app.get("/", response_class=HTMLResponse)
def root_page(request: Request):
    return RedirectResponse(url="/dashboard")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/loginadmin", response_class=HTMLResponse)
def login_admin_page(request: Request):
    return templates.TemplateResponse(request=request, name="login_admin.html")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_session(request, db)
    sync_all_cups_logs(db)
    
    # Calculate pages used this month (matches user MSNV or system admin print jobs)
    pages_used = db.query(func.sum(PrintLog.page_count * PrintLog.copies))\
                   .filter((PrintLog.msnv == current_user.msnv) | (PrintLog.msnv == 'admin')).scalar() or 0

    user_info = {
        "msnv": current_user.msnv,
        "fullname": current_user.fullname,
        "department": current_user.department,
        "quota": current_user.page_quota,
        "used": pages_used,
        "role": current_user.role
    }

    # Fetch user's recent print logs
    user_logs = db.query(PrintLog).filter((PrintLog.msnv == current_user.msnv) | (PrintLog.msnv == 'admin'))\
                  .order_by(PrintLog.printed_at.desc()).limit(10).all()

    return templates.TemplateResponse(
        request=request, 
        name="dashboard.html", 
        context={
            "user": user_info,
            "user_logs": user_logs
        }
    )

@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_session(request, db)
    if current_user.role != "admin":
        return RedirectResponse(url="/loginadmin")

    sync_all_cups_logs(db)
    users = db.query(User).all()
    logs = db.query(PrintLog).order_by(PrintLog.printed_at.desc()).limit(50).all()
    
    # Total statistics
    total_prints = db.query(func.sum(PrintLog.page_count * PrintLog.copies)).scalar() or 0
    total_users = db.query(User).count()
    
    return templates.TemplateResponse(
        request=request, 
        name="admin.html", 
        context={
            "user": current_user,
            "users": users,
            "logs": logs,
            "total_prints": total_prints,
            "total_users": total_users
        }
    )

