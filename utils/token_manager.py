"""
Token management utilities for JWT authentication.
Handles token creation, validation, and storage.
"""
import jwt
from datetime import datetime, timezone, timedelta
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class TokenManager:
    """
    Manages JWT token creation, validation, and storage.
    """
    
    SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    if not SECRET_KEY:
        raise EnvironmentError("JWT_SECRET_KEY is not set. Add it to your .env file.")
    ALGORITHM = 'HS256'
    TOKEN_EXPIRATION_HOURS = 24
    TOKEN_FILE = Path.home() / '.epicevents_token'
    
    @classmethod
    def create_token(cls, user_id: int, employee_number: str, department: str) -> str:
        """
        Create a JWT token for a user.
        
        Args:
            user_id: User's database ID
            employee_number: User's employee number
            department: User's department
            
        Returns:
            Encoded JWT token
        """
        payload = {
            'user_id': user_id,
            'employee_number': employee_number,
            'department': department,
            'exp': datetime.now(timezone.utc) + timedelta(hours=cls.TOKEN_EXPIRATION_HOURS),
            'iat': datetime.now(timezone.utc)
        }
        
        token = jwt.encode(payload, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
        return token
    
    @classmethod
    def decode_token(cls, token: str) -> dict:
        """
        Decode and validate a JWT token.
        
        Args:
            token: JWT token to decode
            
        Returns:
            Decoded payload dictionary
            
        Raises:
            jwt.ExpiredSignatureError: If token has expired
            jwt.InvalidTokenError: If token is invalid
        """
        payload = jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])
        return payload
    
    @classmethod
    def save_token(cls, token: str) -> None:
        """
        Save token to local file for persistent authentication.
        
        Args:
            token: JWT token to save
        """
        cls.TOKEN_FILE.write_text(token)
    
    @classmethod
    def load_token(cls) -> str | None:
        """
        Load token from local file.
        
        Returns:
            Token string if exists, None otherwise
        """
        if cls.TOKEN_FILE.exists():
            return cls.TOKEN_FILE.read_text().strip()
        return None
    
    @classmethod
    def delete_token(cls) -> None:
        """
        Delete the stored token file.
        """
        if cls.TOKEN_FILE.exists():
            cls.TOKEN_FILE.unlink()
    
    @classmethod
    def get_current_user(cls) -> dict | None:
        """
        Get current authenticated user from stored token.
        
        Returns:
            User payload dictionary if token is valid, None otherwise
        """
        token = cls.load_token()
        if not token:
            return None
        
        try:
            payload = cls.decode_token(token)
            return payload
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            # Token is invalid or expired, delete it
            cls.delete_token()
            return None
