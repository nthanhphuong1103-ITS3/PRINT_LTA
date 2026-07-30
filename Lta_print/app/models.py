from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    msnv = Column(String(50), unique=True, index=True, nullable=False)  # Mã nhân viên
    fullname = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    department = Column(String(100))
    password = Column(String(255), nullable=True)  # Mật khẩu quản trị
    role = Column(String(20), default="user")  # 'admin' hoặc 'user'
    is_active = Column(Boolean, default=True)
    page_quota = Column(Integer, default=500)  # Số trang tối đa được in/tháng
    created_at = Column(DateTime, default=datetime.utcnow)

    logs = relationship("PrintLog", back_populates="user")


class PrintLog(Base):
    __tablename__ = "print_logs"

    id = Column(Integer, primary_key=True, index=True)
    msnv = Column(String(50), ForeignKey("users.msnv"), nullable=False)
    printer_name = Column(String(50), nullable=False)
    document_name = Column(String(255), nullable=False)
    page_count = Column(Integer, default=1)
    copies = Column(Integer, default=1)
    file_type = Column(String(20), default="PDF/Doc")
    printed_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="logs")
