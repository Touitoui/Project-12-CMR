import re
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship, validates
from .base import Base


class Client(Base):
    """
    Client model representing customer information.
    
    Attributes:
        id: Unique identifier
        full_name: Complete name of the client
        email: Client's email address
        phone: Client's phone number
        company_name: Name of the client's company
        creation_date: Date of first contact with the client
        last_update: Date of last contact/update
        sales_contact: Name of the commercial contact at Epic Events
    """
    __tablename__ = 'clients'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20), nullable=True)
    company_name = Column(String(100), nullable=True)
    creation_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_update = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    sales_contact = Column(String(100), nullable=True) 
    
    @validates('email')
    def validate_email(self, key, value):
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', value):
            raise ValueError("Invalid email address")
        return value

    # Relationships
    contracts = relationship("Contract", back_populates="client", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.full_name}', email='{self.email}', company='{self.company_name}')>"
    
    def __str__(self):
        return f"{self.full_name} - {self.email} ({self.company_name})"
