import click
import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch

from views.client_view import ClientView
from views.contract_view import ContractView
from views.event_view import EventView
from views.user_view import UserView
from views.auth_view import AuthView


# ---------------------------------------------------------------------------
# ClientView
# ---------------------------------------------------------------------------

class TestClientViewList:
    def test_list_clients_empty(self):
        ctrl = MagicMock()
        ctrl.get_all_clients_with_contacts.return_value = []
        ClientView(ctrl).list_clients()
        ctrl.get_all_clients_with_contacts.assert_called_once()

    def test_list_clients_with_rows(self):
        ctrl = MagicMock()
        mock_client = MagicMock(id=1, full_name="Alice", email="a@b.com",
                                phone="0600", company_name="ACME", sales_contact="EMP1")
        mock_user = MagicMock(full_name="Bob", employee_number="EMP1")
        ctrl.get_all_clients_with_contacts.return_value = [(mock_client, mock_user)]
        ClientView(ctrl).list_clients()  # should not raise
        ctrl.get_all_clients_with_contacts.assert_called_once()


class TestClientViewCreate:
    def test_create_client(self):
        ctrl = MagicMock()
        mock_client = MagicMock(full_name="Alice", id=42, sales_contact="EMP1")
        ctrl.create_client.return_value = mock_client

        view = ClientView(ctrl)

        @click.command()
        def cmd():
            view.create_client()

        result = CliRunner().invoke(cmd, input="Alice\nalice@test.com\n0600\nACME\n")
        assert result.exit_code == 0, result.output
        ctrl.create_client.assert_called_once_with({
            "full_name":    "Alice",
            "email":        "alice@test.com",
            "phone":        "0600",
            "company_name": "ACME",
        })

    def test_create_client_optional_fields_blank(self):
        ctrl = MagicMock()
        ctrl.create_client.return_value = MagicMock(full_name="Bob", id=1, sales_contact="EMP2")

        view = ClientView(ctrl)

        @click.command()
        def cmd():
            view.create_client()

        result = CliRunner().invoke(cmd, input="Bob\nbob@test.com\n\n\n")
        assert result.exit_code == 0, result.output
        ctrl.create_client.assert_called_once_with({
            "full_name":    "Bob",
            "email":        "bob@test.com",
            "phone":        None,
            "company_name": None,
        })


class TestClientViewUpdate:
    def test_update_client_nothing_to_update(self):
        ctrl = MagicMock()
        view = ClientView(ctrl)

        @click.command()
        def cmd():
            view.update_client()

        # Client ID then all blank fields → "Nothing to update"
        result = CliRunner().invoke(cmd, input="1\n\n\n\n\n")
        assert result.exit_code == 0, result.output
        ctrl.update_client.assert_not_called()

    def test_update_client_full_name(self):
        ctrl = MagicMock()
        ctrl.update_client.return_value = MagicMock(full_name="Alice2", id=1)
        view = ClientView(ctrl)

        @click.command()
        def cmd():
            view.update_client()

        result = CliRunner().invoke(cmd, input="1\nAlice2\n\n\n\n")
        assert result.exit_code == 0, result.output
        call_args = ctrl.update_client.call_args
        assert call_args[0][0] == 1
        assert call_args[0][1]["full_name"] == "Alice2"


# ---------------------------------------------------------------------------
# ContractView
# ---------------------------------------------------------------------------

class TestContractViewList:
    def test_list_all_empty(self):
        ctrl = MagicMock()
        ctrl.get_all_contracts.return_value = []
        ContractView(ctrl).list_all_contracts()
        ctrl.get_all_contracts.assert_called_once()

    def test_list_unsigned_empty(self):
        ctrl = MagicMock()
        ctrl.get_unsigned_contracts.return_value = []
        ContractView(ctrl).list_unsigned_contracts()
        ctrl.get_unsigned_contracts.assert_called_once()

    def test_list_unpaid_empty(self):
        ctrl = MagicMock()
        ctrl.get_unpaid_contracts.return_value = []
        ContractView(ctrl).list_unpaid_contracts()
        ctrl.get_unpaid_contracts.assert_called_once()


class TestContractViewCreate:
    def test_create_contract_with_explicit_remaining(self):
        ctrl = MagicMock()
        ctrl.create_contract.return_value = MagicMock(id=5, total_amount=1000.0, is_signed=False)
        view = ContractView(ctrl)

        @click.command()
        def cmd():
            view.create_contract()

        result = CliRunner().invoke(cmd, input="2\n1000\n500\n")
        assert result.exit_code == 0, result.output
        ctrl.create_contract.assert_called_once_with({
            "client_id":        2,
            "total_amount":     1000.0,
            "remaining_amount": 500.0,
        })

    def test_create_contract_remaining_defaults_to_total(self):
        ctrl = MagicMock()
        ctrl.create_contract.return_value = MagicMock(id=6, total_amount=200.0, is_signed=False)
        view = ContractView(ctrl)

        @click.command()
        def cmd():
            view.create_contract()

        # Leave remaining blank → defaults to total
        result = CliRunner().invoke(cmd, input="3\n200\n\n")
        assert result.exit_code == 0, result.output
        ctrl.create_contract.assert_called_once_with({
            "client_id":        3,
            "total_amount":     200.0,
            "remaining_amount": 200.0,
        })


class TestContractViewSign:
    def test_sign_contract(self):
        ctrl = MagicMock()
        ctrl.sign_contract.return_value = MagicMock(id=7)
        view = ContractView(ctrl)

        @click.command()
        def cmd():
            view.sign_contract()

        result = CliRunner().invoke(cmd, input="7\n")
        assert result.exit_code == 0, result.output
        ctrl.sign_contract.assert_called_once_with(7)


# ---------------------------------------------------------------------------
# EventView
# ---------------------------------------------------------------------------

class TestEventViewList:
    def test_list_all_events_empty(self):
        ctrl = MagicMock()
        ctrl.get_all_events.return_value = []
        EventView(ctrl).list_all_events()
        ctrl.get_all_events.assert_called_once()

    def test_list_events_without_support(self):
        ctrl = MagicMock()
        ctrl.get_events_without_support.return_value = []
        EventView(ctrl).list_events_without_support()
        ctrl.get_events_without_support.assert_called_once()

    def test_list_my_events(self):
        ctrl = MagicMock()
        ctrl.get_my_events.return_value = []
        EventView(ctrl).list_my_events()
        ctrl.get_my_events.assert_called_once()


class TestEventViewCreate:
    def test_create_event(self):
        ctrl = MagicMock()
        ctrl.create_event.return_value = MagicMock(id=10, client_name="ACME Corp")
        view = EventView(ctrl)

        @click.command()
        def cmd():
            view.create_event()

        user_input = "\n".join([
            "1",                    # contract_id
            "ACME Corp",            # client_name
            "",                     # title (optional)
            "",                     # client_contact (optional)
            "2025-06-01 09:00",     # start
            "2025-06-01 18:00",     # end
            "",                     # location (optional)
            "",                     # attendees (optional)
            "",                     # notes (optional)
            "",
        ])
        result = CliRunner().invoke(cmd, input=user_input)
        assert result.exit_code == 0, result.output
        ctrl.create_event.assert_called_once()
        call_data = ctrl.create_event.call_args[0][0]
        assert call_data["contract_id"] == 1
        assert call_data["client_name"] == "ACME Corp"

    def test_assign_event(self):
        ctrl = MagicMock()
        ctrl.assign_event.return_value = MagicMock(id=10, support_contact="EMP5")
        view = EventView(ctrl)

        @click.command()
        def cmd():
            view.assign_event()

        result = CliRunner().invoke(cmd, input="10\nEMP5\n")
        assert result.exit_code == 0, result.output
        ctrl.assign_event.assert_called_once_with(10, "EMP5")


# ---------------------------------------------------------------------------
# UserView
# ---------------------------------------------------------------------------

class TestUserViewList:
    def test_list_users_empty(self):
        ctrl = MagicMock()
        ctrl.get_all_users.return_value = []
        UserView(ctrl).list_users()
        ctrl.get_all_users.assert_called_once()

    def test_list_users_with_data(self):
        from models.user import Department
        ctrl = MagicMock()
        ctrl.get_all_users.return_value = [
            MagicMock(id=1, employee_number="EMP1", full_name="Alice",
                      email="a@b.com", department=Department.COMMERCIAL)
        ]
        UserView(ctrl).list_users()
        ctrl.get_all_users.assert_called_once()


class TestUserViewCreate:
    def test_create_user(self):
        ctrl = MagicMock()
        ctrl.create_user.return_value = MagicMock(full_name="Alice", employee_number="EMP1")
        view = UserView(ctrl)

        @click.command()
        def cmd():
            view.create_user()

        user_input = "\n".join([
            "EMP1",             # employee_number
            "Alice Smith",      # full_name
            "alice@test.com",   # email
            "Secret123",        # password
            "Secret123",        # password confirmation
            "commercial",       # department
            "",
        ])
        result = CliRunner().invoke(cmd, input=user_input)
        assert result.exit_code == 0, result.output
        ctrl.create_user.assert_called_once()
        call_data = ctrl.create_user.call_args[0][0]
        assert call_data["employee_number"] == "EMP1"
        assert call_data["email"] == "alice@test.com"


# ---------------------------------------------------------------------------
# AuthView  (uses input() / getpass — patch instead of CliRunner)
# ---------------------------------------------------------------------------

class TestAuthView:
    def test_login_success(self):
        ctrl = MagicMock()
        ctrl.get_current_user.return_value = None
        ctrl.login.return_value = {
            "success": True,
            "message": "Login successful",
            "user": {"department": "commercial"},
        }
        view = AuthView(ctrl)

        with patch("builtins.input", side_effect=["EMP1"]), \
             patch("getpass.getpass", return_value="secret"):
            result = view.login()

        assert result is True
        ctrl.login.assert_called_once_with("EMP1", "secret")

    def test_login_failure(self):
        ctrl = MagicMock()
        ctrl.get_current_user.return_value = None
        ctrl.login.return_value = {"success": False, "message": "Bad credentials"}
        view = AuthView(ctrl)

        with patch("builtins.input", side_effect=["EMP1"]), \
             patch("getpass.getpass", return_value="wrong"):
            result = view.login()

        assert result is False

    def test_logout(self):
        ctrl = MagicMock()
        ctrl.get_current_user.return_value = {"employee_number": "EMP1"}
        ctrl.logout.return_value = {"message": "Logged out"}
        AuthView(ctrl).logout()
        ctrl.logout.assert_called_once()

    def test_logout_not_logged_in(self):
        ctrl = MagicMock()
        ctrl.get_current_user.return_value = None
        AuthView(ctrl).logout()  # should not raise, just echo message
        ctrl.logout.assert_not_called()

    def test_show_current_user_logged_in(self):
        ctrl = MagicMock()
        ctrl.get_current_user.return_value = {
            "employee_number": "EMP1",
            "department": "commercial",
            "user_id": 1,
        }
        AuthView(ctrl).show_current_user()  # should not raise

    def test_show_current_user_not_logged_in(self):
        ctrl = MagicMock()
        ctrl.get_current_user.return_value = None
        AuthView(ctrl).show_current_user()  # should not raise
