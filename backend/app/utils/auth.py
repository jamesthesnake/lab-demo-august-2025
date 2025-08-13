"""
Authentication utilities
Simple placeholder authentication for development
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
import os

# Secret key for JWT (in production, use environment variable)
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

async def get_current_user(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Get current user from token (placeholder)
    In production, this would validate the token and return user info
    """
    # For development, return a default user
    return {
        "user_id": "default_user",
        "username": "developer",
        "email": "developer@aidolab.local",
        "is_active": True
    }

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token
    
    Args:
        token: JWT token to verify
    
    Returns:
        Decoded token data or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

# Optional: Basic API key authentication for simplicity
def verify_api_key(api_key: str) -> bool:
    """
    Verify API key (placeholder)
    
    Args:
        api_key: API key to verify
    
    Returns:
        True if valid, False otherwise
    """
    # In production, check against database or environment variable
    valid_api_keys = [
        os.getenv("API_KEY", "test-api-key-123")
    ]
    return api_key in valid_api_keys

