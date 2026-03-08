import click
from argon2 import PasswordHasher
from rich.console import Console
from rich.table import Table
from rich import box

from controllers.user_controller import UserController
from models.user import Department

console = Console()
_ph = PasswordHasher()

DEPARTMENTS = [d.value for d in Department]


class UserView:

    def __init__(self, controller: UserController):
        self.controller = controller

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    def list_users(self) -> None:
        users = self.controller.get_all_users()
        if not users:
            console.print("[yellow]No users found.[/yellow]")
            return
        table = Table(title="Users", box=box.ROUNDED, highlight=True)
        table.add_column("ID", style="dim", justify="right")
        table.add_column("Employee #", style="cyan")
        table.add_column("Full Name", style="bold")
        table.add_column("Email")
        table.add_column("Department", style="magenta")
        for u in users:
            table.add_row(str(u.id), u.employee_number, u.full_name, u.email, u.department.value)
        console.print(table)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_user(self) -> None:
        console.print("\n[bold cyan]=== Create User ===[/bold cyan]")
        employee_number = click.prompt("Employee number")
        full_name       = click.prompt("Full name")
        email           = click.prompt("Email")
        password        = click.prompt("Password", hide_input=True, confirmation_prompt=True)
        dept_str        = click.prompt(
            f"Department ({'/'.join(DEPARTMENTS)})",
            type=click.Choice(DEPARTMENTS, case_sensitive=False)
        )
        department = Department(dept_str.lower())

        user = self.controller.create_user({
            "employee_number": employee_number,
            "full_name":       full_name,
            "email":           email,
            "password_hash":   _ph.hash(password),
            "department":      department,
        })
        console.print(f"[green]✔ User created:[/green] {user.full_name} ({user.employee_number}) — {user.department.value}")

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_user(self) -> None:
        console.print("\n[bold cyan]=== Update User ===[/bold cyan]")
        user_id = click.prompt("User ID", type=int)

        full_name        = click.prompt("Full name        (leave blank to keep)", default="", show_default=False)
        email            = click.prompt("Email            (leave blank to keep)", default="", show_default=False)
        new_password     = click.prompt("New password     (leave blank to keep)", default="", show_default=False, hide_input=True)
        dept_str         = click.prompt(
            f"Department ({'/'.join(DEPARTMENTS)}) (leave blank to keep)",
            default="", show_default=False
        )

        update_data = {}
        if full_name:    update_data["full_name"]     = full_name
        if email:        update_data["email"]         = email
        if new_password: update_data["password_hash"] = _ph.hash(new_password)
        if dept_str:     update_data["department"]    = Department(dept_str.lower())

        if not update_data:
            console.print("[yellow]Nothing to update.[/yellow]")
            return

        user = self.controller.update_user(user_id, update_data)
        console.print(f"[green]✔ User updated:[/green] {user.full_name} ({user.employee_number}) — {user.department.value}")

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_user(self) -> None:
        console.print("\n[bold red]=== Delete User ===[/bold red]")
        user_id = click.prompt("User ID", type=int)
        if not click.confirm(f"Delete user #{user_id}? This cannot be undone"):
            console.print("[yellow]Cancelled.[/yellow]")
            return
        self.controller.delete_user(user_id)
        console.print(f"[green]✔ User #{user_id} deleted.[/green]")