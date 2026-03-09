import re
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import validates
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import enum
from .base import Base


class Department(enum.Enum):
    """
    Department enumeration for user affiliation.
    Each department has different permissions.
    """
    COMMERCIAL = "commercial"
    SUPPORT = "support"
    GESTION = "gestion"


class User(Base):
    """
    User model representing employees using the application.
    
    Attributes:
        id: Unique identifier
        employee_number: Unique employee identification number
        full_name: Complete name of the employee
        email: Employee's email address
        password_hash: Hashed password using Argon2
        department: Department affiliation (commercial, support, or gestion)
        creation_date: Date when the user account was created
        last_login: Date of last login
    """
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_number = Column(String(50), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    department = Column(Enum(Department), nullable=False)
    creation_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    @validates('email')
    def validate_email(self, key, value):
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', value):
            raise ValueError("Invalid email address")
        return value

    # Password hasher instance
    _ph = PasswordHasher()
    
    def set_password(self, password: str) -> None:
        """
        Hash and set the user's password using Argon2.
        
        Args:
            password: Plain text password to hash
        """
        self.password_hash = self._ph.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """
        Verify a password against the stored hash.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            self._ph.verify(self.password_hash, password)
            # Check if rehashing is needed (Argon2 will update parameters over time)
            if self._ph.check_needs_rehash(self.password_hash):
                self.set_password(password)
            return True
        except VerifyMismatchError:
            return False
    
    def __repr__(self):
        return f"<User(id={self.id}, employee_number='{self.employee_number}', name='{self.full_name}', department='{self.department.value}')>"
    
    def __str__(self):
        return f"{self.full_name} ({self.employee_number}) - {self.department.value}"
