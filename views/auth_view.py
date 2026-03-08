"""
Authentication view - handles user interaction for authentication.
"""
import getpass
from controllers.auth_controller import AuthController
import click


class AuthView:
    """
    View for authentication operations.
    Handles user input/output for login and logout.
    """
    
    def __init__(self, controller: AuthController):
        """
        Initialize authentication view.
        
        Args:
            controller: AuthController instance
        """
        self.controller = controller
    
    def login(self) -> bool:
        """
        Display login prompt and handle user authentication.
        
        Returns:
            True if login successful, False otherwise
        """
        click.echo("\n=== Epic Events CRM - Login ===")
        
        # Check if already logged in
        current_user = self.controller.get_current_user()
        if current_user:
            click.echo(f"Already logged in as {current_user['employee_number']} ({current_user['department']})")
            response = input("Do you want to logout and login as different user? (y/n): ").lower()
            if response == 'y':
                self.controller.logout()
            else:
                return True
        
        # Get credentials
        employee_number = input("Employee Number: ").strip()
        password = getpass.getpass("Password: ")
        
        # Attempt login
        result = self.controller.login(employee_number, password)
        
        if result['success']:
            click.echo(f"\n {result['message']}")
            user = result['user']
            click.echo(f"  Department: {user['department']}")
            click.echo(f"  Session token saved.\n")
            return True
        else:
            click.echo(f"\n {result['message']}\n")
            return False
    
    def logout(self) -> None:
        """
        Display logout confirmation and handle logout.
        """
        current_user = self.controller.get_current_user()
        
        if not current_user:
            click.echo("\n You are not logged in.\n")
            return
        
        click.echo(f"\n=== Logout ===")
        click.echo(f"Currently logged in as: {current_user['employee_number']}")
        
        result = self.controller.logout()
        click.echo(f" {result['message']}\n")
    
    def show_current_user(self) -> None:
        """
        Display current user information.
        """
        current_user = self.controller.get_current_user()
        
        if not current_user:
            click.echo("\n Not logged in.\n")
            return
        
        click.echo("\n=== Current Session ===")
        click.echo(f"Employee Number: {current_user['employee_number']}")
        click.echo(f"Department: {current_user['department']}")
        click.echo(f"User ID: {current_user['user_id']}\n")
    
    def require_authentication(self) -> bool:
        """
        Check if user is authenticated, show error if not.
        
        Returns:
            True if authenticated, False otherwise
        """
        is_authenticated, message = self.controller.require_auth()
        
        if not is_authenticated:
            click.echo(f"\n {message}")
            click.echo("  Please login first using: python epicevents.py login\n")
            return False
        
        return True
