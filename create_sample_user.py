"""
Script to create one sample user per department for testing.
Run once after initialising the database:
    python create_sample_user.py
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from rich.console import Console
from rich.table import Table
from rich import box

from models.base import Base
from models.user import User, Department

console = Console()

# One sample account per department
SAMPLE_USERS = [
    {
        "employee_number": "EMP_GES",
        "full_name":       "Alice Gestion",
        "email":           "alice.gestion@epicevents.com",
        "department":      Department.GESTION,
        "password":        "123",
    },
    {
        "employee_number": "EMP_COM",
        "full_name":       "Bob Commercial",
        "email":           "bob.commercial@epicevents.com",
        "department":      Department.COMMERCIAL,
        "password":        "123",
    },
    {
        "employee_number": "EMP_SUP",
        "full_name":       "Carol Support",
        "email":           "carol.support@epicevents.com",
        "department":      Department.SUPPORT,
        "password":        "123",
    },
]


def create_sample_users():
    DATABASE_URL = "sqlite:///epicevents.db"

    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    created = []
    skipped = []

    try:
        for data in SAMPLE_USERS:
            existing = session.query(User).filter_by(
                employee_number=data["employee_number"]
            ).first()

            if existing:
                skipped.append(existing)
                continue

            user = User(
                employee_number=data["employee_number"],
                full_name=data["full_name"],
                email=data["email"],
                department=data["department"],
            )
            user.set_password(data["password"])
            session.add(user)
            created.append((user, data["password"]))

        session.commit()
        for user, _ in created:
            session.refresh(user)

    except Exception as e:
        session.rollback()
        console.print(f"[red]Error: {e}[/red]")
        return
    finally:
        session.close()

    # ── Results table ───────────────────────────────────────────────
    table = Table(title="Sample Users", box=box.ROUNDED, highlight=True)
    table.add_column("Status",      justify="center")
    table.add_column("Employee #",  style="cyan")
    table.add_column("Full Name",   style="bold")
    table.add_column("Email")
    table.add_column("Department",  style="magenta")
    table.add_column("Password",    style="dim")

    for user, password in created:
        table.add_row(
            "[green]Created[/green]",
            user.employee_number, user.full_name, user.email,
            user.department.value, password,
        )
    for user in skipped:
        table.add_row(
            "[yellow]Skipped[/yellow]",
            user.employee_number, user.full_name, user.email,
            user.department.value, "(already exists)",
        )

    console.print(table)
    console.print("\nLogin with:  [bold]python epicevents.py login[/bold]\n")


if __name__ == "__main__":
    create_sample_users()
