from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .database import get_db
from .models import User

def get_current_user_from_session(request: Request, db: Session = Depends(get_db)):
    """
    Extracts current logged in user from cookie session.
    Defaults to demo employee (MSNV: 4642) if no explicit session cookie present.
    """
    msnv = request.cookies.get("msnv", "4642")
    user = db.query(User).filter(User.msnv == msnv).first()
    
    if not user:
        # Auto seed default test user if not present
        user = User(
            msnv="4642",
            fullname="Nguyen Van A",
            email="a.nguyen@company.com",
            department="IT Team",
            role="user",  # Default role is user
            page_quota=500,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
    return user


def require_admin(user: User = Depends(get_current_user_from_session)):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Truy cập bị từ chối. Chỉ dành cho Admin."
        )
    return user
