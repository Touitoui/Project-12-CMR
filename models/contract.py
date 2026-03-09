from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship, validates
from .base import Base


class Contract(Base):
    """
    Contract model representing contracts between Epic Events and clients.
    
    Attributes:
        id: Unique contract identifier
        client_id: Reference to the associated client
        sales_contact: Sales person associated with the client/contract
        total_amount: Total contract amount
        remaining_amount: Amount still to be paid
        creation_date: Date when the contract was created
        is_signed: Contract status (whether it has been signed)
    """
    __tablename__ = 'contracts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    sales_contact = Column(String(100), nullable=False)
    total_amount = Column(Float, nullable=False, default=0.0)
    remaining_amount = Column(Float, nullable=False, default=0.0)
    creation_date = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    is_signed = Column(Boolean, default=False, nullable=False)
    
    @validates('total_amount')
    def validate_total_amount(self, key, value):
        if value < 0:
            raise ValueError("Total amount cannot be negative.")
        return value

    @validates('remaining_amount')
    def validate_remaining_amount(self, key, value):
        if value < 0:
            raise ValueError("Remaining amount cannot be negative.")
        if self.total_amount is not None and value > self.total_amount:
            raise ValueError("Remaining amount cannot exceed total amount.")
        return value

    # Relationships
    client = relationship("Client", back_populates="contracts")
    events = relationship("Event", back_populates="contract", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Contract(id={self.id}, client_id={self.client_id}, total={self.total_amount}, signed={self.is_signed})>"
    
    def __str__(self):
        status = "Signé" if self.is_signed else "Non signé"
        return f"Contrat #{self.id} - {self.sales_contact} - {self.total_amount}€ ({status})"
    
    @property
    def paid_amount(self):
        """Calculate the amount already paid."""
        return self.total_amount - self.remaining_amount
    
    @property
    def is_fully_paid(self):
        """Check if the contract is fully paid."""
        return self.remaining_amount <= 0
    
    @property
    def payment_percentage(self):
        """Calculate the percentage of payment completed."""
        if self.total_amount > 0:
            return (self.paid_amount / self.total_amount) * 100
        return 0.0
