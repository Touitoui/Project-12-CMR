"""
Integration tests for all controllers.
Covers CRUD operations and permission enforcement for:
  - AuthController    (login / logout / get_current_user)
  - UserController    (GESTION only for write)
  - ClientController  (COMMERCIAL only, own clients)
  - ContractController(COMMERCIAL + GESTION, with ownership rules)
  - EventController   (COMMERCIAL create, GESTION+SUPPORT update, filters)
"""
import pytest
from unittest.mock import patch
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.base import Base
from models.user import User, Department
from models.client import Client
from models.contract import Contract
from models.event import Event

from controllers.user_controller import UserController
from controllers.client_controller import ClientController
from controllers.contract_controller import ContractController
from controllers.event_controller import EventController
from controllers.auth_controller import AuthController


# ---------------------------------------------------------------------------
# Database fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session():
    """Fresh in-memory SQLite for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Helper: seed the acting user into the DB and return a matching token dict.
# ---------------------------------------------------------------------------

def seed_actor(session, employee_number: str, department: Department) -> dict:
    """Insert the acting user into the DB and return the token payload."""
    # Avoid duplicates when multiple helpers share the same employee_number
    existing = session.query(User).filter_by(employee_number=employee_number).first()
    if existing:
        return {
            "user_id": existing.id,
            "employee_number": existing.employee_number,
            "department": existing.department.value,
        }
    user = User(
        employee_number=employee_number,
        full_name=f"John {employee_number}",
        email=f"{employee_number.lower()}@test.com",
        department=department,
        password_hash="hashed",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return {
        "user_id": user.id,
        "employee_number": user.employee_number,
        "department": user.department.value,
    }


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def seed_client(session, sales_contact: str, email: str = "client@test.com") -> Client:
    client = Client(
        full_name="Test Client",
        email=email,
        phone="0600000000",
        company_name="TestCo",
        sales_contact=sales_contact,
    )
    session.add(client)
    session.commit()
    session.refresh(client)
    return client


def seed_contract(
    session, client: Client, sales_contact: str, is_signed: bool = False, remaining: float = 1000.0
) -> Contract:
    contract = Contract(
        client_id=client.id,
        sales_contact=sales_contact,
        total_amount=5000.0,
        remaining_amount=remaining,
        is_signed=is_signed,
    )
    session.add(contract)
    session.commit()
    session.refresh(contract)
    return contract


def seed_event(session, contract: Contract, support_contact: str = "") -> Event:
    event = Event(
        contract_id=contract.id,
        client_name=contract.client.full_name,
        event_date_start=datetime(2026, 6, 1, 10, 0),
        event_date_end=datetime(2026, 6, 1, 18, 0),
        support_contact=support_contact,
        location="Paris",
        attendees=50,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


# ===========================================================================
# UserController Tests
# ===========================================================================

class TestUserController:
    """GESTION can create / update / delete users. Others cannot."""

    def _ctrl(self, db_session):
        auth = AuthController(db_session)
        return UserController(db_session, auth)

    # --- create_user --------------------------------------------------------

    def test_gestion_can_create_user(self, db_session):
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            user = ctrl.create_user(
                {
                    "employee_number": "E001",
                    "full_name": "Alice Dupont",
                    "email": "alice@test.com",
                    "department": Department.COMMERCIAL,
                    "password_hash": "hashed",
                }
            )
        assert user.id is not None
        assert user.employee_number == "E001"

    def test_commercial_cannot_create_user(self, db_session):
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.create_user(
                    {
                        "employee_number": "E002",
                        "full_name": "Bob",
                        "email": "bob@test.com",
                        "department": Department.SUPPORT,
                        "password_hash": "hashed",
                    }
                )

    def test_support_cannot_create_user(self, db_session):
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "S001", Department.SUPPORT)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.create_user(
                    {
                        "employee_number": "E003",
                        "full_name": "Carol",
                        "email": "carol@test.com",
                        "department": Department.SUPPORT,
                        "password_hash": "hashed",
                    }
                )

    # --- update_user --------------------------------------------------------

    def test_gestion_can_update_user_department(self, db_session):
        user = User(
            employee_number="E010",
            full_name="Dave",
            email="dave@test.com",
            department=Department.COMMERCIAL,
            password_hash="hashed",
        )
        db_session.add(user)
        db_session.commit()

        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            updated = ctrl.update_user(user.id, {"department": Department.SUPPORT})
        assert updated.department == Department.SUPPORT

    def test_commercial_cannot_update_user(self, db_session):
        user = User(
            employee_number="E011",
            full_name="Eve",
            email="eve@test.com",
            department=Department.SUPPORT,
            password_hash="hashed",
        )
        db_session.add(user)
        db_session.commit()

        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.update_user(user.id, {"full_name": "Eve Modified"})

    # --- delete_user --------------------------------------------------------

    def test_gestion_can_delete_user(self, db_session):
        user = User(
            employee_number="E020",
            full_name="Frank",
            email="frank@test.com",
            department=Department.COMMERCIAL,
            password_hash="hashed",
        )
        db_session.add(user)
        db_session.commit()
        uid = user.id

        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            result = ctrl.delete_user(uid)
        assert result is True
        assert db_session.query(User).filter(User.id == uid).first() is None

    # --- unauthenticated ----------------------------------------------------

    def test_unauthenticated_cannot_create_user(self, db_session):
        ctrl = self._ctrl(db_session)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=None):
            with pytest.raises(PermissionError):
                ctrl.create_user({})


# ===========================================================================
# ClientController Tests
# ===========================================================================

class TestClientController:
    """COMMERCIAL creates clients (auto-assigned). Only responsible commercial updates."""

    def _ctrl(self, db_session):
        auth = AuthController(db_session)
        return ClientController(db_session, auth)

    def test_commercial_can_create_client(self, db_session):
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            client = ctrl.create_client(
                {
                    "full_name": "Grace Client",
                    "email": "grace@client.com",
                    "phone": "0600000001",
                    "company_name": "GraceCo",
                }
            )
        assert client.id is not None
        assert client.sales_contact == "C001"

    def test_gestion_cannot_create_client(self, db_session):
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.create_client({"full_name": "X", "email": "x@test.com"})

    def test_commercial_can_update_own_client(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="own@test.com")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            updated = ctrl.update_client(client.id, {"full_name": "Updated Name"})
        assert updated.full_name == "Updated Name"

    def test_commercial_cannot_update_other_client(self, db_session):
        client = seed_client(db_session, sales_contact="C999", email="other@test.com")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.update_client(client.id, {"full_name": "Hack"})


# ===========================================================================
# ContractController Tests
# ===========================================================================

class TestContractController:
    """
    COMMERCIAL: create/update own contracts.
    GESTION: create/update any contract, delete contracts.
    """

    def _ctrl(self, db_session):
        auth = AuthController(db_session)
        return ContractController(db_session, auth)

    # --- create_contract ----------------------------------------------------

    def test_commercial_can_create_contract_for_own_client(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="c@test.com")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            contract = ctrl.create_contract(
                {"client_id": client.id, "total_amount": 3000.0, "remaining_amount": 3000.0}
            )
        assert contract.id is not None
        assert contract.sales_contact == "C001"

    def test_commercial_cannot_create_contract_for_other_client(self, db_session):
        client = seed_client(db_session, sales_contact="C999", email="other2@test.com")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.create_contract(
                    {"client_id": client.id, "total_amount": 3000.0, "remaining_amount": 3000.0}
                )

    def test_gestion_can_create_contract_for_any_client(self, db_session):
        client = seed_client(db_session, sales_contact="C999", email="any@test.com")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            contract = ctrl.create_contract(
                {"client_id": client.id, "total_amount": 2000.0, "remaining_amount": 2000.0}
            )
        assert contract.id is not None

    def test_support_cannot_create_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="s@test.com")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "S001", Department.SUPPORT)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.create_contract({"client_id": client.id, "total_amount": 1000.0, "remaining_amount": 1000.0})

    # --- update_contract ----------------------------------------------------

    def test_commercial_can_update_own_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="upd@test.com")
        contract = seed_contract(db_session, client, sales_contact="C001")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            updated = ctrl.update_contract(contract.id, {"total_amount": 9999.0})
        assert updated.total_amount == 9999.0

    def test_commercial_cannot_update_other_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C999", email="upd2@test.com")
        contract = seed_contract(db_session, client, sales_contact="C999")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.update_contract(contract.id, {"total_amount": 1.0})

    def test_gestion_can_update_any_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="gest@test.com")
        contract = seed_contract(db_session, client, sales_contact="C001")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            updated = ctrl.update_contract(contract.id, {"is_signed": True, "sales_contact": "C001"})
        assert updated.is_signed is True

    # --- delete_contract ----------------------------------------------------

    def test_gestion_can_delete_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="del@test.com")
        contract = seed_contract(db_session, client, sales_contact="C001")
        cid = contract.id
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            result = ctrl.delete_contract(cid)
        assert result is True
        assert db_session.query(Contract).filter(Contract.id == cid).first() is None

    def test_commercial_cannot_delete_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="del2@test.com")
        contract = seed_contract(db_session, client, sales_contact="C001")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.delete_contract(contract.id)

    # --- filters ------------------------------------------------------------

    def test_get_unsigned_contracts(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="flt@test.com")
        seed_contract(db_session, client, "C001", is_signed=False)
        seed_contract(db_session, client, "C001", is_signed=True)
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            unsigned = ctrl.get_unsigned_contracts()
        assert len(unsigned) == 1
        assert unsigned[0].is_signed is False

    def test_get_unpaid_contracts(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="flt2@test.com")
        seed_contract(db_session, client, "C001", remaining=500.0)
        seed_contract(db_session, client, "C001", remaining=0.0)
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            unpaid = ctrl.get_unpaid_contracts()
        assert len(unpaid) == 1
        assert unpaid[0].remaining_amount == 500.0


# ===========================================================================
# EventController Tests
# ===========================================================================

class TestEventController:
    """
    COMMERCIAL: create events for signed contracts they own.
    GESTION: update any event (e.g. assign support), delete, filter without support.
    SUPPORT: update own events, filter own events.
    """

    def _ctrl(self, db_session):
        auth = AuthController(db_session)
        return EventController(db_session, auth)

    # --- create_event -------------------------------------------------------

    def test_commercial_can_create_event_for_signed_own_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="ev1@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            event = ctrl.create_event(
                {
                    "contract_id": contract.id,
                    "client_name": client.full_name,
                    "event_date_start": datetime(2026, 7, 1, 9, 0),
                    "event_date_end": datetime(2026, 7, 1, 17, 0),
                    "location": "Lyon",
                    "attendees": 100,
                }
            )
        assert event.id is not None

    def test_commercial_cannot_create_event_for_unsigned_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="ev2@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=False)
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.create_event(
                    {
                        "contract_id": contract.id,
                        "client_name": client.full_name,
                        "event_date_start": datetime(2026, 7, 1, 9, 0),
                        "event_date_end": datetime(2026, 7, 1, 17, 0),
                    }
                )

    def test_commercial_cannot_create_event_for_other_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C999", email="ev3@test.com")
        contract = seed_contract(db_session, client, "C999", is_signed=True)
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.create_event(
                    {
                        "contract_id": contract.id,
                        "client_name": client.full_name,
                        "event_date_start": datetime(2026, 7, 1, 9, 0),
                        "event_date_end": datetime(2026, 7, 1, 17, 0),
                    }
                )

    def test_support_cannot_create_event(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="ev4@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "S001", Department.SUPPORT)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.create_event(
                    {
                        "contract_id": contract.id,
                        "client_name": client.full_name,
                        "event_date_start": datetime(2026, 7, 1, 9, 0),
                        "event_date_end": datetime(2026, 7, 1, 17, 0),
                    }
                )

    # --- update_event -------------------------------------------------------

    def test_gestion_can_update_any_event(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="ev5@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        event = seed_event(db_session, contract, support_contact="")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            updated = ctrl.update_event(event.id, {"support_contact": "S001"})
        assert updated.support_contact == "S001"

    def test_support_can_update_own_event(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="ev6@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        event = seed_event(db_session, contract, support_contact="S001")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "S001", Department.SUPPORT)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            updated = ctrl.update_event(event.id, {"location": "Marseille"})
        assert updated.location == "Marseille"

    def test_support_cannot_update_other_support_event(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="ev7@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        event = seed_event(db_session, contract, support_contact="S999")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "S001", Department.SUPPORT)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.update_event(event.id, {"location": "Bordeaux"})

    def test_commercial_cannot_update_event(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="ev8@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        event = seed_event(db_session, contract, support_contact="S001")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.update_event(event.id, {"location": "Nice"})

    # --- delete_event -------------------------------------------------------

    def test_gestion_can_delete_event(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="ev9@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        event = seed_event(db_session, contract)
        eid = event.id
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            result = ctrl.delete_event(eid)
        assert result is True
        assert db_session.query(Event).filter(Event.id == eid).first() is None

    def test_support_cannot_delete_event(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="ev10@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        event = seed_event(db_session, contract, support_contact="S001")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "S001", Department.SUPPORT)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.delete_event(event.id)

    # --- filters ------------------------------------------------------------

    def test_gestion_get_events_without_support(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="fev1@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        seed_event(db_session, contract, support_contact="")
        seed_event(db_session, contract, support_contact="S001")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            results = ctrl.get_events_without_support()
        assert len(results) == 1
        assert results[0].support_contact == ""

    def test_commercial_cannot_get_events_without_support(self, db_session):
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.get_events_without_support()

    def test_support_get_my_events(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="fev2@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        seed_event(db_session, contract, support_contact="S001")
        seed_event(db_session, contract, support_contact="S002")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "S001", Department.SUPPORT)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            results = ctrl.get_my_events()
        assert len(results) == 1
        assert results[0].support_contact == "S001"

    def test_gestion_cannot_call_get_my_events(self, db_session):
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.get_my_events()


# ===========================================================================
# Workflow Test — full natural execution order (see diagram)
# ===========================================================================

class TestWorkflow:
    """
    End-to-end test following the natural business workflow:

    1. COMMERCIAL démarchage → crée un client (auto-assigné)
    2. Client souhaite un événement → GESTION crée et associe un contrat
    3. Client signe → GESTION marque le contrat comme signé
    4. COMMERCIAL crée l'événement sur la plateforme
    5. GESTION désigne un membre du support sur l'événement
    6. SUPPORT met à jour / organise l'événement
    """

    def test_full_workflow(self, db_session):
        auth = AuthController(db_session)
        user_ctrl     = UserController(db_session, auth)
        client_ctrl   = ClientController(db_session, auth)
        contract_ctrl = ContractController(db_session, auth)
        event_ctrl    = EventController(db_session, auth)

        # ------------------------------------------------------------------
        # Étape 0 – GESTION crée les collaborateurs
        # ------------------------------------------------------------------
        # seed_actor inserts each actor into the DB so permission checks pass.
        gestion_token    = seed_actor(db_session, "G001", Department.GESTION)

        with patch("utils.token_manager.TokenManager.get_current_user", return_value=gestion_token):
            commercial = user_ctrl.create_user({
                "employee_number": "C001",
                "full_name": "Alice Commercial",
                "email": "alice@epicevents.com",
                "department": Department.COMMERCIAL,
                "password_hash": "hashed",
            })
            support = user_ctrl.create_user({
                "employee_number": "S001",
                "full_name": "Bob Support",
                "email": "bob@epicevents.com",
                "department": Department.SUPPORT,
                "password_hash": "hashed",
            })

        # Build tokens for the users.
        commercial_token = {
            "user_id": commercial.id,
            "employee_number": commercial.employee_number,
            "department": commercial.department.value,
        }
        support_token = {
            "user_id": support.id,
            "employee_number": support.employee_number,
            "department": support.department.value,
        }

        assert commercial.department == Department.COMMERCIAL
        assert support.department == Department.SUPPORT

        # ------------------------------------------------------------------
        # Étape 1 – COMMERCIAL démarchage → crée un nouveau client
        #           (le commercial est automatiquement associé)
        # ------------------------------------------------------------------
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=commercial_token):
            client = client_ctrl.create_client({
                "full_name": "Sophie Durand",
                "email": "sophie@acmecorp.com",
                "phone": "0612345678",
                "company_name": "Acme Corp",
            })

        assert client.id is not None
        assert client.sales_contact == "C001", "Le client doit être auto-assigné au commercial"

        # ------------------------------------------------------------------
        # Étape 2 – Le client souhaite un événement
        #           → GESTION crée et associe un contrat au client
        # ------------------------------------------------------------------
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=gestion_token):
            contract = contract_ctrl.create_contract({
                "client_id": client.id,
                "total_amount": 10000.0,
                "remaining_amount": 10000.0,
            })

        assert contract.id is not None
        assert contract.client_id == client.id
        assert contract.is_signed is False

        # ------------------------------------------------------------------
        # Étape 3 – Le client signe → GESTION marque le contrat comme signé
        #           et enregistre le paiement partiel
        # ------------------------------------------------------------------
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=gestion_token):
            contract = contract_ctrl.update_contract(contract.id, {
                "is_signed": True,
                "remaining_amount": 5000.0,  # acompte versé
            })

        assert contract.is_signed is True
        assert contract.remaining_amount == 5000.0

        # ------------------------------------------------------------------
        # Étape 4 – COMMERCIAL crée l'événement sur la plateforme
        #           (uniquement possible car le contrat est signé)
        # ------------------------------------------------------------------
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=commercial_token):
            event = event_ctrl.create_event({
                "contract_id": contract.id,
                "client_name": client.full_name,
                "event_date_start": datetime(2026, 9, 15, 9, 0),
                "event_date_end":   datetime(2026, 9, 15, 18, 0),
                "location": "Paris Expo",
                "attendees": 200,
                "notes": "Gala annuel Acme Corp",
            })

        assert event.id is not None
        assert event.support_contact in (None, ""), "Aucun support assigné à ce stade"

        # ------------------------------------------------------------------
        # Étape 5 – GESTION désigne un membre du support sur l'événement
        # ------------------------------------------------------------------
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=gestion_token):
            event = event_ctrl.update_event(event.id, {"support_contact": "S001"})

        assert event.support_contact == "S001"

        # Vérification : GESTION peut lister les événements sans support → liste vide maintenant
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=gestion_token):
            without_support = event_ctrl.get_events_without_support()
        assert len(without_support) == 0, "Tous les événements ont un support assigné"

        # ------------------------------------------------------------------
        # Étape 6 – SUPPORT organise et met à jour l'événement
        # ------------------------------------------------------------------
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=support_token):
            event = event_ctrl.update_event(event.id, {
                "location": "Paris Expo — Salle Étoile",
                "attendees": 220,
                "notes": "Gala annuel Acme Corp — salle mise à jour",
            })

        assert event.location == "Paris Expo — Salle Étoile"
        assert event.attendees == 220

        with patch("utils.token_manager.TokenManager.get_current_user", return_value=support_token):
            event = event_ctrl.update_event(event.id, {
                "location": "Paris Expo — Salle Étoile",
                "attendees": 220,
                "notes": "Gala annuel Acme Corp — salle mise à jour",
            })

        assert event.location == "Paris Expo — Salle Étoile"
        assert event.attendees == 220

        # SUPPORT peut voir ses propres événements
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=support_token):
            my_events = event_ctrl.get_my_events()
        assert len(my_events) == 1
        assert my_events[0].id == event.id


# ===========================================================================
# AuthController Tests
# ===========================================================================

class TestAuthController:
    """Login, logout, and get_current_user behaviour."""

    def test_login_success(self, db_session):
        user = User(
            employee_number="AUTH001",
            full_name="Auth User",
            email="auth@test.com",
            department=Department.GESTION,
        )
        user.set_password("GoodPass1!")
        db_session.add(user)
        db_session.commit()

        auth = AuthController(db_session)
        result = auth.login("AUTH001", "GoodPass1!")

        assert result["success"] is True
        assert "token" in result
        assert result["user"]["employee_number"] == "AUTH001"

        # Clean up token file so other tests are not affected.
        from utils.token_manager import TokenManager
        TokenManager.delete_token()

    def test_login_wrong_password(self, db_session):
        user = User(
            employee_number="AUTH002",
            full_name="Auth User 2",
            email="auth2@test.com",
            department=Department.COMMERCIAL,
        )
        user.set_password("RealPass1!")
        db_session.add(user)
        db_session.commit()

        auth = AuthController(db_session)
        result = auth.login("AUTH002", "WrongPass!")

        assert result["success"] is False
        assert "token" not in result

    def test_login_unknown_employee(self, db_session):
        auth = AuthController(db_session)
        result = auth.login("NOBODY", "anything")
        assert result["success"] is False

    def test_logout(self, db_session):
        auth = AuthController(db_session)
        result = auth.logout()
        assert result["success"] is True

    def test_get_current_user_with_valid_token(self, db_session):
        user = User(
            employee_number="AUTH003",
            full_name="Auth User 3",
            email="auth3@test.com",
            department=Department.SUPPORT,
        )
        user.set_password("Pass1!")
        db_session.add(user)
        db_session.commit()

        token_payload = {
            "user_id": user.id,
            "employee_number": user.employee_number,
            "department": user.department.value,
        }
        auth = AuthController(db_session)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token_payload):
            current = auth.get_current_user()

        assert current is not None
        assert current["employee_number"] == "AUTH003"

    def test_get_current_user_deleted_account(self, db_session):
        """If the token references a deleted user, get_current_user returns None."""
        token_payload = {
            "user_id": 9999,  # does not exist
            "employee_number": "GHOST",
            "department": "gestion",
        }
        auth = AuthController(db_session)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token_payload):
            current = auth.get_current_user()

        assert current is None


# ===========================================================================
# ContractController — sign_contract & read helpers
# ===========================================================================

class TestContractControllerExtra:
    """Tests for sign_contract, get_contract_by_id, get_all_contracts."""

    def _ctrl(self, db_session):
        return ContractController(db_session, AuthController(db_session))

    def test_gestion_can_sign_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="sign1@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=False)
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            signed = ctrl.sign_contract(contract.id)
        assert signed.is_signed is True

    def test_commercial_can_sign_own_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="sign2@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=False)
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            signed = ctrl.sign_contract(contract.id)
        assert signed.is_signed is True

    def test_commercial_cannot_sign_other_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C999", email="sign3@test.com")
        contract = seed_contract(db_session, client, "C999", is_signed=False)
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.sign_contract(contract.id)

    def test_sign_nonexistent_contract_raises(self, db_session):
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(ValueError):
                ctrl.sign_contract(9999)

    def test_get_contract_by_id(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="gbid@test.com")
        contract = seed_contract(db_session, client, "C001")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            found = ctrl.get_contract_by_id(contract.id)
        assert found is not None
        assert found.id == contract.id

    def test_get_all_contracts(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="gall@test.com")
        seed_contract(db_session, client, "C001")
        seed_contract(db_session, client, "C001")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            contracts = ctrl.get_all_contracts()
        assert len(contracts) == 2


# ===========================================================================
# EventController — assign_event & read helpers
# ===========================================================================

class TestEventControllerExtra:
    """Tests for assign_event, get_event_by_id, get_events_by_contract."""

    def _ctrl(self, db_session):
        return EventController(db_session, AuthController(db_session))

    def _seed_support_user(self, db_session, employee_number: str = "S001") -> User:
        existing = db_session.query(User).filter_by(employee_number=employee_number).first()
        if existing:
            return existing
        user = User(
            employee_number=employee_number,
            full_name=f"Support {employee_number}",
            email=f"{employee_number.lower()}@support.test",
            department=Department.SUPPORT,
            password_hash="hashed",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def test_gestion_can_assign_support_to_event(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="asgn1@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        event = seed_event(db_session, contract, support_contact="")
        support_user = self._seed_support_user(db_session, "S001")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            updated = ctrl.assign_event(event.id, support_user.employee_number)
        assert updated.support_contact == "S001"

    def test_assign_nonexistent_support_raises(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="asgn2@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        event = seed_event(db_session, contract)
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(ValueError):
                ctrl.assign_event(event.id, "NOBODY")

    def test_assign_non_support_user_raises(self, db_session):
        """assign_event should reject assigning a COMMERCIAL user as support contact."""
        client = seed_client(db_session, sales_contact="C001", email="asgn3@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        event = seed_event(db_session, contract)
        # Seed a COMMERCIAL actor so the DB row exists for the assign target
        commercial_user = seed_actor(db_session, "C001", Department.COMMERCIAL)
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(ValueError):
                ctrl.assign_event(event.id, "C001")

    def test_commercial_cannot_assign_event(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="asgn4@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        event = seed_event(db_session, contract)
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.assign_event(event.id, "S001")

    def test_get_event_by_id(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="gbid_ev@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        event = seed_event(db_session, contract)
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            found = ctrl.get_event_by_id(event.id)
        assert found is not None
        assert found.id == event.id

    def test_get_events_by_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="gbc@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        seed_event(db_session, contract)
        seed_event(db_session, contract)
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            events = ctrl.get_events_by_contract(contract.id)
        assert len(events) == 2


# ===========================================================================
# UserController — read helpers
# ===========================================================================

class TestUserControllerExtra:
    """Tests for get_user_by_id, get_all_users, get_users_by_department."""

    def _ctrl(self, db_session):
        return UserController(db_session, AuthController(db_session))

    def test_get_user_by_id(self, db_session):
        user = User(
            employee_number="RD001",
            full_name="Read User",
            email="read@test.com",
            department=Department.SUPPORT,
            password_hash="hashed",
        )
        db_session.add(user)
        db_session.commit()

        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            found = ctrl.get_user_by_id(user.id)
        assert found is not None
        assert found.employee_number == "RD001"

    def test_get_all_users(self, db_session):
        for i in range(3):
            u = User(
                employee_number=f"U00{i}",
                full_name=f"User {i}",
                email=f"u{i}@test.com",
                department=Department.COMMERCIAL,
                password_hash="hashed",
            )
            db_session.add(u)
        db_session.commit()

        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            users = ctrl.get_all_users()
        # 3 seeded + 1 actor (G001)
        assert len(users) >= 3

    def test_get_users_by_department(self, db_session):
        for i in range(2):
            u = User(
                employee_number=f"SUPP00{i}",
                full_name=f"Support {i}",
                email=f"supp{i}@test.com",
                department=Department.SUPPORT,
                password_hash="hashed",
            )
            db_session.add(u)
        db_session.commit()

        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "G001", Department.GESTION)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            support_users = ctrl.get_users_by_department(Department.SUPPORT)
        assert len(support_users) == 2


# ===========================================================================
# ClientController — read helpers
# ===========================================================================

class TestClientControllerExtra:
    """Tests for get_client_by_id, get_all_clients, get_all_clients_with_contacts."""

    def _ctrl(self, db_session):
        return ClientController(db_session, AuthController(db_session))

    def test_get_client_by_id(self, db_session):
        client = seed_client(db_session, "C001", email="cbyid@test.com")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            found = ctrl.get_client_by_id(client.id)
        assert found is not None
        assert found.id == client.id

    def test_get_all_clients(self, db_session):
        seed_client(db_session, "C001", email="ca1@test.com")
        seed_client(db_session, "C001", email="ca2@test.com")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            clients = ctrl.get_all_clients()
        assert len(clients) == 2

    def test_get_all_clients_with_contacts(self, db_session):
        actor = seed_actor(db_session, "C001", Department.COMMERCIAL)
        seed_client(db_session, "C001", email="cwc1@test.com")
        ctrl = self._ctrl(db_session)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=actor):
            results = ctrl.get_all_clients_with_contacts()
        assert len(results) == 1
        client_obj, sales_user = results[0]
        assert client_obj.sales_contact == "C001"
        # The sales user should be resolved from the DB
        assert sales_user is not None
        assert sales_user.employee_number == "C001"

    def test_commercial_can_delete_own_client(self, db_session):
        client = seed_client(db_session, "C001", email="cdel@test.com")
        ctrl = self._ctrl(db_session)
        token = seed_actor(db_session, "C001", Department.COMMERCIAL)
        cid = client.id
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            result = ctrl.delete_client(cid)
        assert result is True
        assert db_session.query(Client).filter(Client.id == cid).first() is None
