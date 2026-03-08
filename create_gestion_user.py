"""
Interactive script to create a GESTION user.
Run after initialising the database:
    python create_gestion_user.py
"""
import getpass

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from rich.console import Console
from rich.table import Table
from rich import box

from models.base import Base
from models.user import User, Department

console = Console()


def prompt_non_empty(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        console.print(f"[red]{label} cannot be empty.[/red]")


def prompt_password() -> str:
    while True:
        password = getpass.getpass("Password: ")
        if not password:
            console.print("[red]Password cannot be empty.[/red]")
            continue
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            console.print("[red]Passwords do not match. Please try again.[/red]")
            continue
        return password


def create_gestion_user():
    console.print("\n[bold cyan]Create a new GESTION user[/bold cyan]\n")

    employee_number = prompt_non_empty("Employee number")
    full_name = prompt_non_empty("Full name")
    email = prompt_non_empty("Email")
    password = prompt_password()

    DATABASE_URL = "sqlite:///epicevents.db"
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        if session.query(User).filter_by(employee_number=employee_number).first():
            console.print(f"[yellow]A user with employee number '{employee_number}' already exists.[/yellow]")
            return
        if session.query(User).filter_by(email=email).first():
            console.print(f"[yellow]A user with email '{email}' already exists.[/yellow]")
            return

        user = User(
            employee_number=employee_number,
            full_name=full_name,
            email=email,
            department=Department.GESTION,
        )
        user.set_password(password)
        session.add(user)
        session.commit()
        session.refresh(user)

    except Exception as e:
        session.rollback()
        console.print(f"[red]Error: {e}[/red]")
        return
    finally:
        session.close()

    table = Table(title="Gestion User Created", box=box.ROUNDED, highlight=True)
    table.add_column("Employee #", style="cyan")
    table.add_column("Full Name", style="bold")
    table.add_column("Email")
    table.add_column("Department", style="magenta")

    table.add_row(
        user.employee_number,
        user.full_name,
        user.email,
        user.department.value,
    )

    console.print(table)
    console.print("\nLogin with:  [bold]python epicevents.py auth login[/bold]\n")


if __name__ == "__main__":
    create_gestion_user()
