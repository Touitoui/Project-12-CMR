#!/usr/bin/env python3
"""
Epic Events CRM - Main CLI Entry Point
"""
import os
import sys
import click
import sentry_sdk

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    traces_sample_rate=1.0,
)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from controllers.auth_controller import AuthController
from controllers.user_controller import UserController
from controllers.contract_controller import ContractController
from controllers.client_controller import ClientController
from controllers.event_controller import EventController

from views.auth_view import AuthView
from views.user_view import UserView
from views.client_view import ClientView
from views.contract_view import ContractView
from views.event_view import EventView


def get_db_session():
    """
    Create and return a database session.
    Modify the database URL according to your setup.
    """
    # TODO: Update with actual database URL
    DATABASE_URL = "sqlite:///test.db"

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()


# ---------------------------------------------------------------------------
# Root CLI group — initialises DB + views once, shared via context object
# ---------------------------------------------------------------------------

@click.group()
@click.pass_context
def cli(ctx):
    """Epic Events CRM - Customer Relationship Management System."""
    ctx.ensure_object(dict)
    db = get_db_session()

    auth_controller = AuthController(db)
    user_controller = UserController(db, auth_controller)
    contract_controller = ContractController(db, auth_controller)
    client_controller = ClientController(db, auth_controller)
    event_controller = EventController(db, auth_controller)

    ctx.obj['auth_view'] = AuthView(auth_controller)
    ctx.obj['user_view'] = UserView(user_controller)
    ctx.obj['client_view'] = ClientView(client_controller)
    ctx.obj['contract_view'] = ContractView(contract_controller)
    ctx.obj['event_view'] = EventView(event_controller)
    ctx.obj['db'] = db
    ctx.call_on_close(db.close)


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------

@cli.group()
def auth():
    """Authentication commands."""
    pass


@auth.command()
@click.pass_obj
def login(obj):
    """Log in with your credentials."""
    obj['auth_view'].login()


@auth.command()
@click.pass_obj
def logout(obj):
    """Log out the current user."""
    obj['auth_view'].logout()


@auth.command()
@click.pass_obj
def whoami(obj):
    """Show the currently logged-in user."""
    obj['auth_view'].show_current_user()


# ---------------------------------------------------------------------------
# users  (GESTION only)
# ---------------------------------------------------------------------------

@cli.group()
def users():
    """User management commands (GESTION role only)."""
    pass


@users.command(name='list')
@click.pass_obj
def list_users(obj):
    """List all users."""
    obj['user_view'].list_users()


@users.command(name='create')
@click.pass_obj
def create_user(obj):
    """Create a new user."""
    obj['user_view'].create_user()


@users.command(name='update')
@click.pass_obj
def update_user(obj):
    """Update an existing user."""
    obj['user_view'].update_user()


@users.command(name='delete')
@click.pass_obj
def delete_user(obj):
    """Delete a user."""
    obj['user_view'].delete_user()


# ---------------------------------------------------------------------------
# clients
# ---------------------------------------------------------------------------

@cli.group()
def clients():
    """Client management commands."""
    pass


@clients.command(name='list')
@click.pass_obj
def list_clients(obj):
    """List all clients."""
    obj['client_view'].list_clients()


@clients.command(name='create')
@click.pass_obj
def create_client(obj):
    """Create a new client."""
    obj['client_view'].create_client()


@clients.command(name='update')
@click.pass_obj
def update_client(obj):
    """Update an existing client."""
    obj['client_view'].update_client()


# ---------------------------------------------------------------------------
# contracts
# ---------------------------------------------------------------------------

@cli.group()
def contracts():
    """Contract management commands."""
    pass


@contracts.command(name='list')
@click.pass_obj
def list_contracts(obj):
    """List all contracts."""
    obj['contract_view'].list_all_contracts()


@contracts.command(name='list-unsigned')
@click.pass_obj
def list_unsigned(obj):
    """List contracts that have not been signed yet."""
    obj['contract_view'].list_unsigned_contracts()


@contracts.command(name='list-unpaid')
@click.pass_obj
def list_unpaid(obj):
    """List contracts with an outstanding balance."""
    obj['contract_view'].list_unpaid_contracts()


@contracts.command(name='create')
@click.pass_obj
def create_contract(obj):
    """Create a new contract."""
    obj['contract_view'].create_contract()


@contracts.command(name='update')
@click.pass_obj
def update_contract(obj):
    """Update an existing contract."""
    obj['contract_view'].update_contract()


@contracts.command(name='sign')
@click.pass_obj
def sign_contract(obj):
    """Mark a contract as signed."""
    obj['contract_view'].sign_contract()


# ---------------------------------------------------------------------------
# events
# ---------------------------------------------------------------------------

@cli.group()
def events():
    """Event management commands."""
    pass


@events.command(name='list')
@click.pass_obj
def list_events(obj):
    """List all events."""
    obj['event_view'].list_all_events()


@events.command(name='list-no-support')
@click.pass_obj
def list_no_support(obj):
    """List events that have no support contact assigned."""
    obj['event_view'].list_events_without_support()


@events.command(name='list-mine')
@click.pass_obj
def list_my_events(obj):
    """List events assigned to the current user."""
    obj['event_view'].list_my_events()


@events.command(name='create')
@click.pass_obj
def create_event(obj):
    """Create a new event."""
    obj['event_view'].create_event()


@events.command(name='update')
@click.pass_obj
def update_event(obj):
    """Update an existing event."""
    obj['event_view'].update_event()


@events.command(name='assign')
@click.pass_obj
def assign_event(obj):
    """Assign a support contact to an event."""
    obj['event_view'].assign_event()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    try:
        cli()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        print(f"\nError: {e}\n")
        sys.exit(1)
