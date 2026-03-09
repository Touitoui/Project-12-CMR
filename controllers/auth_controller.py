"""
Authentication controller - handles authentication business logic.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.user import User
from utils.token_manager import TokenManager


class AuthController:
    """
    Controller for authentication operations.
    Handles login, logout, and authorization logic.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize authentication controller.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
    
    def login(self, employee_number: str, password: str) -> dict:
        """
        Authenticate a user and create a JWT token.
        
        Args:
            employee_number: User's employee number
            password: User's password
            
        Returns:
            Dictionary with success status, message, and token if successful
        """
        # Find user by employee number
        user = self.db_session.query(User).filter_by(employee_number=employee_number).first()
        
        if not user:
            return {
                'success': False,
                'message': 'Invalid employee number or password.'
            }
        
        # Verify password
        if not user.verify_password(password):
            return {
                'success': False,
                'message': 'Invalid employee number or password.'
            }
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        self.db_session.commit()
        
        # Create JWT token
        token = TokenManager.create_token(
            user_id=user.id,
            employee_number=user.employee_number,
            department=user.department.value
        )
        
        # Save token locally
        TokenManager.save_token(token)
        
        return {
            'success': True,
            'message': f'Welcome {user.full_name}!',
            'token': token,
            'user': {
                'id': user.id,
                'employee_number': user.employee_number,
                'full_name': user.full_name,
                'department': user.department.value
            }
        }
    
    def logout(self) -> dict:
        """
        Logout current user by deleting stored token.
        
        Returns:
            Dictionary with success status and message
        """
        TokenManager.delete_token()
        return {
            'success': True,
            'message': 'Logged out successfully.'
        }
    
    def get_current_user(self) -> dict | None:
        """
        Get currently authenticated user information.
        Verifies the user account still exists in the database.

        Returns:
            User information dictionary if authenticated, None otherwise
        """
        payload = TokenManager.get_current_user()
        if not payload:
            return None
        user = self.db_session.query(User).filter_by(id=payload['user_id']).first()
        if not user:
            TokenManager.delete_token()
            return None
        return payload
    
    def check_permission(self, required_department: str) -> bool:
        """
        Check if current user has required department permission.
        
        Args:
            required_department: Required department name (commercial, support, gestion)
            
        Returns:
            True if user has permission, False otherwise
        """
        current_user = self.get_current_user()
        
        if not current_user:
            raise PermissionError("You must be logged in to perform this action.")
        
        if current_user['department'] != required_department:
            raise PermissionError(f"Only {required_department} department can perform this action.")
        
        return True
    
    def require_auth(self) -> tuple[bool, str]:
        """
        Check if user is authenticated.
        
        Returns:
            Tuple of (is_authenticated, message)
        """
        current_user = self.get_current_user()
        
        if not current_user:
            return False, 'You must be logged in to perform this action.'
        
        return True, ''
