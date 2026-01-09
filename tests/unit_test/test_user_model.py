"""
Test suite for the User model using pytest.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from models import Base, User, Department


@pytest.fixture(scope='function')
def db_session():
    """
    Create a fresh in-memory database session for each test (in memory = no persistence).
    """
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()


@pytest.fixture
def sample_user():
    """
    Create a sample user instance.
    """
    user = User(
        employee_number="EMP001",
        full_name="Jean Dupont",
        email="jean.dupont@epicevents.com",
        department=Department.COMMERCIAL
    )
    user.set_password("SecurePassword123!")
    return user


class TestUserModel:
    """Test cases for the User model."""
    
    def test_create_user(self, db_session, sample_user):
        """Test creating a new user."""
        db_session.add(sample_user)
        db_session.commit()
        
        assert sample_user.id is not None
        assert sample_user.employee_number == "EMP001"
        assert sample_user.full_name == "Jean Dupont"
        assert sample_user.email == "jean.dupont@epicevents.com"
        assert sample_user.department == Department.COMMERCIAL
    
    def test_password_hashing(self, sample_user):
        """Test that passwords are properly hashed."""
        assert sample_user.password_hash is not None
        assert sample_user.password_hash != "SecurePassword123!"
        assert sample_user.password_hash.startswith("$argon2id$")
    
    def test_password_verification_success(self, sample_user):
        """Test password verification with correct password."""
        assert sample_user.verify_password("SecurePassword123!") is True
    
    def test_password_verification_failure(self, sample_user):
        """Test password verification with incorrect password."""
        assert sample_user.verify_password("WrongPassword") is False
    
    def test_unique_employee_number(self, db_session, sample_user):
        """Test that employee numbers must be unique."""
        db_session.add(sample_user)
        db_session.commit()
        
        # Try to create another user with the same employee number
        duplicate_user = User(
            employee_number="EMP001",  # Duplicate
            full_name="Another User",
            email="another@epicevents.com",
            department=Department.SUPPORT
        )
        duplicate_user.set_password("password123")
        
        db_session.add(duplicate_user)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_unique_email(self, db_session, sample_user):
        """Test that emails must be unique."""
        db_session.add(sample_user)
        db_session.commit()
        
        # Try to create another user with the same email
        duplicate_user = User(
            employee_number="EMP002",
            full_name="Another User",
            email="jean.dupont@epicevents.com",  # Duplicate
            department=Department.SUPPORT
        )
        duplicate_user.set_password("password123")
        
        db_session.add(duplicate_user)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_all_departments(self, db_session):
        """Test creating users in all departments."""
        users = [
            User(
                employee_number="EMP001",
                full_name="Commercial User",
                email="commercial@epicevents.com",
                department=Department.COMMERCIAL
            ),
            User(
                employee_number="EMP002",
                full_name="Support User",
                email="support@epicevents.com",
                department=Department.SUPPORT
            ),
            User(
                employee_number="EMP003",
                full_name="Gestion User",
                email="gestion@epicevents.com",
                department=Department.GESTION
            )
        ]
        
        for user in users:
            user.set_password("password123")
        
        db_session.add_all(users)
        db_session.commit()
        
        # Query and verify
        commercial = db_session.query(User).filter_by(department=Department.COMMERCIAL).first()
        support = db_session.query(User).filter_by(department=Department.SUPPORT).first()
        gestion = db_session.query(User).filter_by(department=Department.GESTION).first()
        
        assert commercial.full_name == "Commercial User"
        assert support.full_name == "Support User"
        assert gestion.full_name == "Gestion User"
    
    def test_query_by_department(self, db_session):
        """Test querying users by department."""
        # Create multiple users in the same department
        user1 = User(
            employee_number="EMP001",
            full_name="User One",
            email="user1@epicevents.com",
            department=Department.COMMERCIAL
        )
        user1.set_password("pass1")
        
        user2 = User(
            employee_number="EMP002",
            full_name="User Two",
            email="user2@epicevents.com",
            department=Department.COMMERCIAL
        )
        user2.set_password("pass2")
        
        user3 = User(
            employee_number="EMP003",
            full_name="User Three",
            email="user3@epicevents.com",
            department=Department.SUPPORT
        )
        user3.set_password("pass3")
        
        db_session.add_all([user1, user2, user3])
        db_session.commit()
        
        commercial_users = db_session.query(User).filter_by(department=Department.COMMERCIAL).all()
        
        assert len(commercial_users) == 2
        assert all(u.department == Department.COMMERCIAL for u in commercial_users)
    
