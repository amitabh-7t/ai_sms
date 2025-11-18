from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
import logging

from ..models import UserSignup, UserLogin, Token, TokenData
from ..config import config
from ..db import get_db, Database

logger = logging.getLogger(__name__)
router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Database = Depends(get_db)
):
    """Dependency to get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = await db.fetch_one(
        "SELECT id, email, full_name, is_admin FROM users WHERE email = $1",
        token_data.email
    )
    
    if user is None:
        raise credentials_exception
    
    return user

@router.post("/signup", response_model=Token)
async def signup(user: UserSignup, db: Database = Depends(get_db)):
    """Register new user - restricted unless admin"""
    
    # Check if user already exists
    existing = await db.fetch_one(
        "SELECT id FROM users WHERE email = $1",
        user.email
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = get_password_hash(user.password)
    
    # Check if this is first user (make them admin)
    user_count = await db.fetch_one("SELECT COUNT(*) as count FROM users")
    is_admin = user_count["count"] == 0
    
    # Insert user
    try:
        await db.execute(
            """
            INSERT INTO users (email, password_hash, full_name, is_admin, created_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            user.email, hashed_password, user.full_name, is_admin, datetime.utcnow()
        )
        logger.info(f"User created: {user.email} (admin={is_admin})")
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(user: UserLogin, db: Database = Depends(get_db)):
    """Login user"""
    
    # Get user
    db_user = await db.fetch_one(
        "SELECT id, email, password_hash FROM users WHERE email = $1",
        user.email
    )
    
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    
    logger.info(f"User logged in: {user.email}")
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return {
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "is_admin": current_user["is_admin"]
    }