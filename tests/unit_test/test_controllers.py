"""
Integration tests for all controllers.
Covers CRUD operations and permission enforcement for:
  - UserController    (GESTION only for write)
  - ClientController  (COMMERCIAL only, own clients)
  - ContractController(COMMERCIAL + GESTION, with ownership rules)
  - EventController   (COMMERCIAL create, GESTION+SUPPORT update, filters)
"""
import pytest
from unittest.mock import patch
from datetime import datetime
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
# Helper: fake TokenManager.get_current_user
# ---------------------------------------------------------------------------

def make_user_token(employee_number: str, department: str) -> dict:
    return {
        "user_id": 1,
        "employee_number": employee_number,
        "department": department,
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
        token = make_user_token("G001", Department.GESTION.value)
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
        token = make_user_token("C001", Department.COMMERCIAL.value)
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
        token = make_user_token("S001", Department.SUPPORT.value)
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
        token = make_user_token("G001", Department.GESTION.value)
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
        token = make_user_token("C001", Department.COMMERCIAL.value)
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
        token = make_user_token("G001", Department.GESTION.value)
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
        token = make_user_token("C001", Department.COMMERCIAL.value)
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
        token = make_user_token("G001", Department.GESTION.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.create_client({"full_name": "X", "email": "x@test.com"})

    def test_commercial_can_update_own_client(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="own@test.com")
        ctrl = self._ctrl(db_session)
        token = make_user_token("C001", Department.COMMERCIAL.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            updated = ctrl.update_client(client.id, {"full_name": "Updated Name"})
        assert updated.full_name == "Updated Name"

    def test_commercial_cannot_update_other_client(self, db_session):
        client = seed_client(db_session, sales_contact="C999", email="other@test.com")
        ctrl = self._ctrl(db_session)
        token = make_user_token("C001", Department.COMMERCIAL.value)
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
        token = make_user_token("C001", Department.COMMERCIAL.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            contract = ctrl.create_contract(
                {"client_id": client.id, "total_amount": 3000.0, "remaining_amount": 3000.0}
            )
        assert contract.id is not None
        assert contract.sales_contact == "C001"

    def test_commercial_cannot_create_contract_for_other_client(self, db_session):
        client = seed_client(db_session, sales_contact="C999", email="other2@test.com")
        ctrl = self._ctrl(db_session)
        token = make_user_token("C001", Department.COMMERCIAL.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.create_contract(
                    {"client_id": client.id, "total_amount": 3000.0, "remaining_amount": 3000.0}
                )

    def test_gestion_can_create_contract_for_any_client(self, db_session):
        client = seed_client(db_session, sales_contact="C999", email="any@test.com")
        ctrl = self._ctrl(db_session)
        token = make_user_token("G001", Department.GESTION.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            contract = ctrl.create_contract(
                {"client_id": client.id, "total_amount": 2000.0, "remaining_amount": 2000.0}
            )
        assert contract.id is not None

    def test_support_cannot_create_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="s@test.com")
        ctrl = self._ctrl(db_session)
        token = make_user_token("S001", Department.SUPPORT.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.create_contract({"client_id": client.id, "total_amount": 1000.0, "remaining_amount": 1000.0})

    # --- update_contract ----------------------------------------------------

    def test_commercial_can_update_own_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="upd@test.com")
        contract = seed_contract(db_session, client, sales_contact="C001")
        ctrl = self._ctrl(db_session)
        token = make_user_token("C001", Department.COMMERCIAL.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            updated = ctrl.update_contract(contract.id, {"total_amount": 9999.0})
        assert updated.total_amount == 9999.0

    def test_commercial_cannot_update_other_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C999", email="upd2@test.com")
        contract = seed_contract(db_session, client, sales_contact="C999")
        ctrl = self._ctrl(db_session)
        token = make_user_token("C001", Department.COMMERCIAL.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.update_contract(contract.id, {"total_amount": 1.0})

    def test_gestion_can_update_any_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="gest@test.com")
        contract = seed_contract(db_session, client, sales_contact="C001")
        ctrl = self._ctrl(db_session)
        token = make_user_token("G001", Department.GESTION.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            updated = ctrl.update_contract(contract.id, {"is_signed": True, "sales_contact": "C001"})
        assert updated.is_signed is True

    # --- delete_contract ----------------------------------------------------

    def test_gestion_can_delete_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="del@test.com")
        contract = seed_contract(db_session, client, sales_contact="C001")
        cid = contract.id
        ctrl = self._ctrl(db_session)
        token = make_user_token("G001", Department.GESTION.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            result = ctrl.delete_contract(cid)
        assert result is True
        assert db_session.query(Contract).filter(Contract.id == cid).first() is None

    def test_commercial_cannot_delete_contract(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="del2@test.com")
        contract = seed_contract(db_session, client, sales_contact="C001")
        ctrl = self._ctrl(db_session)
        token = make_user_token("C001", Department.COMMERCIAL.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.delete_contract(contract.id)

    # --- filters ------------------------------------------------------------

    def test_get_unsigned_contracts(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="flt@test.com")
        seed_contract(db_session, client, "C001", is_signed=False)
        seed_contract(db_session, client, "C001", is_signed=True)
        ctrl = self._ctrl(db_session)
        token = make_user_token("C001", Department.COMMERCIAL.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            unsigned = ctrl.get_unsigned_contracts()
        assert len(unsigned) == 1
        assert unsigned[0].is_signed is False

    def test_get_unpaid_contracts(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="flt2@test.com")
        seed_contract(db_session, client, "C001", remaining=500.0)
        seed_contract(db_session, client, "C001", remaining=0.0)
        ctrl = self._ctrl(db_session)
        token = make_user_token("C001", Department.COMMERCIAL.value)
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
        token = make_user_token("C001", Department.COMMERCIAL.value)
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
        token = make_user_token("C001", Department.COMMERCIAL.value)
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
        token = make_user_token("C001", Department.COMMERCIAL.value)
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
        token = make_user_token("S001", Department.SUPPORT.value)
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
        token = make_user_token("G001", Department.GESTION.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            updated = ctrl.update_event(event.id, {"support_contact": "S001"})
        assert updated.support_contact == "S001"

    def test_support_can_update_own_event(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="ev6@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        event = seed_event(db_session, contract, support_contact="S001")
        ctrl = self._ctrl(db_session)
        token = make_user_token("S001", Department.SUPPORT.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            updated = ctrl.update_event(event.id, {"location": "Marseille"})
        assert updated.location == "Marseille"

    def test_support_cannot_update_other_support_event(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="ev7@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        event = seed_event(db_session, contract, support_contact="S999")
        ctrl = self._ctrl(db_session)
        token = make_user_token("S001", Department.SUPPORT.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.update_event(event.id, {"location": "Bordeaux"})

    def test_commercial_cannot_update_event(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="ev8@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        event = seed_event(db_session, contract, support_contact="S001")
        ctrl = self._ctrl(db_session)
        token = make_user_token("C001", Department.COMMERCIAL.value)
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
        token = make_user_token("G001", Department.GESTION.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            result = ctrl.delete_event(eid)
        assert result is True
        assert db_session.query(Event).filter(Event.id == eid).first() is None

    def test_support_cannot_delete_event(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="ev10@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        event = seed_event(db_session, contract, support_contact="S001")
        ctrl = self._ctrl(db_session)
        token = make_user_token("S001", Department.SUPPORT.value)
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
        token = make_user_token("G001", Department.GESTION.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            results = ctrl.get_events_without_support()
        assert len(results) == 1
        assert results[0].support_contact == ""

    def test_commercial_cannot_get_events_without_support(self, db_session):
        ctrl = self._ctrl(db_session)
        token = make_user_token("C001", Department.COMMERCIAL.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            with pytest.raises(PermissionError):
                ctrl.get_events_without_support()

    def test_support_get_my_events(self, db_session):
        client = seed_client(db_session, sales_contact="C001", email="fev2@test.com")
        contract = seed_contract(db_session, client, "C001", is_signed=True)
        seed_event(db_session, contract, support_contact="S001")
        seed_event(db_session, contract, support_contact="S002")
        ctrl = self._ctrl(db_session)
        token = make_user_token("S001", Department.SUPPORT.value)
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=token):
            results = ctrl.get_my_events()
        assert len(results) == 1
        assert results[0].support_contact == "S001"

    def test_gestion_cannot_call_get_my_events(self, db_session):
        ctrl = self._ctrl(db_session)
        token = make_user_token("G001", Department.GESTION.value)
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
        gestion_token    = make_user_token("G001", Department.GESTION.value)
        commercial_token = make_user_token("C001", Department.COMMERCIAL.value)
        support_token    = make_user_token("S001", Department.SUPPORT.value)

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

        # SUPPORT peut voir ses propres événements
        with patch("utils.token_manager.TokenManager.get_current_user", return_value=support_token):
            my_events = event_ctrl.get_my_events()
        assert len(my_events) == 1
        assert my_events[0].id == event.id
