from functools import wraps
from utils.token_manager import TokenManager
from models.user import User


def _get_validated_user(db_session):
    """
    Decode the stored token and confirm the user still exists in the database.
    Returns the token payload on success, raises PermissionError otherwise.
    """
    current_user = TokenManager.get_current_user()
    if not current_user:
        raise PermissionError("You must be logged in to perform this action.")
    user = db_session.query(User).filter(User.id == current_user['user_id']).first()
    if not user:
        TokenManager.delete_token()
        raise PermissionError("Your account no longer exists. Please log in again.")
    return current_user


# Decorator to check user permission by department.
# Accepts one or more allowed department values.
# Usage: @check_permission(Department.GESTION.value, Department.COMMERCIAL.value)
def check_permission(*allowed_departments):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            current_user = _get_validated_user(self.db_session)
            if current_user['department'] not in allowed_departments:
                allowed = ", ".join(allowed_departments)
                raise PermissionError(f"Only {allowed} department(s) can perform this action.")
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


# Decorator to check if a user is authenticated (connected)
# Usage: @require_auth
def require_auth(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        _get_validated_user(self.db_session)
        return func(self, *args, **kwargs)
    return wrapper
