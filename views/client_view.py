import click
from rich.console import Console
from rich.table import Table
from rich import box

from controllers.client_controller import ClientController

console = Console()


class ClientView:
	def __init__(self, controller: ClientController):
		self.controller = controller

	# ------------------------------------------------------------------
	# List
	# ------------------------------------------------------------------

	def list_clients(self) -> None:
		rows = self.controller.get_all_clients_with_contacts()
		if not rows:
			console.print("[yellow]No clients found.[/yellow]")
			return
		table = Table(title="Clients", box=box.ROUNDED, highlight=True)
		table.add_column("ID",           style="dim",  justify="right")
		table.add_column("Full Name",    style="bold")
		table.add_column("Email")
		table.add_column("Phone")
		table.add_column("Company")
		table.add_column("Sales Contact", style="cyan")
		for c, user in rows:
			if user:
				contact_str = f"{user.full_name} ({user.employee_number})"
			else:
				contact_str = c.sales_contact or "-"
			table.add_row(
				str(c.id), c.full_name, c.email,
				c.phone or "-", c.company_name or "-", contact_str
			)
		console.print(table)

	# ------------------------------------------------------------------
	# Create
	# ------------------------------------------------------------------

	def create_client(self) -> None:
		console.print("\n[bold cyan]=== Create Client ===[/bold cyan]")
		full_name    = click.prompt("Full name")
		email        = click.prompt("Email")
		phone        = click.prompt("Phone (optional)",   default="", show_default=False) or None
		company_name = click.prompt("Company (optional)", default="", show_default=False) or None

		client = self.controller.create_client({
			"full_name":    full_name,
			"email":        email,
			"phone":        phone,
			"company_name": company_name,
		})
		console.print(f"[green]✔ Client created:[/green] {client.full_name} (ID: {client.id}, assigned to: {client.sales_contact})")

	# ------------------------------------------------------------------
	# Update
	# ------------------------------------------------------------------

	def update_client(self) -> None:
		console.print("\n[bold cyan]=== Update Client ===[/bold cyan]")
		client_id    = click.prompt("Client ID", type=int)
		full_name    = click.prompt("Full name    (leave blank to keep)", default="", show_default=False)
		email        = click.prompt("Email        (leave blank to keep)", default="", show_default=False)
		phone        = click.prompt("Phone        (leave blank to keep)", default="", show_default=False)
		company_name = click.prompt("Company      (leave blank to keep)", default="", show_default=False)

		update_data = {}
		if full_name:    update_data["full_name"]    = full_name
		if email:        update_data["email"]        = email
		if phone:        update_data["phone"]        = phone
		if company_name: update_data["company_name"] = company_name

		if not update_data:
			console.print("[yellow]Nothing to update.[/yellow]")
			return

		client = self.controller.update_client(client_id, update_data)
		console.print(f"[green]✔ Client updated:[/green] {client.full_name} (ID: {client.id})")
