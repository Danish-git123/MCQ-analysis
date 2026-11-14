import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .database import get_db
from .models import User
from .schemas import TokenData

SECRET_KEY = "supersecretkey_for_phase1_mcq"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 300

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72],
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email, role=role)
    except JWTError:
        raise credentials_exception
        
    stmt = select(User).where(User.email == token_data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    return user

async def get_current_teacher(current_user: User = Depends(get_current_user)):
    if current_user.role != "teacher": # type: ignore
        raise HTTPException(status_code=403, detail="Not authorized, requires teacher role")
    return current_user

async def get_current_student(current_user: User = Depends(get_current_user)):
    if current_user.role != "student": # type: ignore
        raise HTTPException(status_code=403, detail="Not authorized, requires student role")
    return current_user
