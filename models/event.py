from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Event(Base):
    """
    Event model representing events organized for clients.
    
    Attributes:
        id: Unique event identifier
        contract_id: Reference to the associated contract
        client_name: Name of the client for this event
        client_email: Client's email contact
        client_phone: Client's phone contact
        event_date_start: Start date and time of the event
        event_date_end: End date and time of the event
        support_contact: Name of the support person assigned
        location: Full address of the event location
        attendees: Number of expected attendees
        notes: Additional notes and details about the event
    """
    # TODO change 1:N to 1:1
    __tablename__ = 'events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey('contracts.id'), nullable=False)
    client_name = Column(String(100), nullable=False)

    title = Column(String(100), nullable=True)
    client_contact = Column(String(255), nullable=True)
    event_date_start = Column(DateTime, nullable=False)
    event_date_end = Column(DateTime, nullable=False)
    support_contact = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)
    attendees = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationship to contract 
    contract = relationship("Contract", back_populates="events")
    
    def __repr__(self):
        return f"<Event(id={self.id}, contract_id={self.contract_id}, client='{self.client_name}', start='{self.event_date_start}')>"
    
    def __str__(self):
        return f"Event #{self.id} - {self.client_name} ({self.event_date_start.strftime('%d %b %Y @ %I%p') if self.event_date_start else 'TBD'})"
    
    @property
    def duration_hours(self):
        """Calculate event duration in hours."""
        if self.event_date_start and self.event_date_end:
            delta = self.event_date_end - self.event_date_start
            return delta.total_seconds() / 3600
        return None
