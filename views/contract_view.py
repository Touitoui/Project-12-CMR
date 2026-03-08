import click
from rich.console import Console
from rich.table import Table
from rich import box

from controllers.contract_controller import ContractController

console = Console()


class ContractView:
	def __init__(self, controller: ContractController):
		self.controller = controller

	# ------------------------------------------------------------------
	# Shared table renderer
	# ------------------------------------------------------------------

	def _render_contracts(self, contracts, title: str) -> None:
		if not contracts:
			console.print(f"[yellow]No contracts found ({title}).[/yellow]")
			return
		table = Table(title=title, box=box.ROUNDED, highlight=True)
		table.add_column("ID",        style="dim",   justify="right")
		table.add_column("Client ID", justify="right")
		table.add_column("Sales Contact", style="cyan")
		table.add_column("Total",     justify="right")
		table.add_column("Remaining", justify="right")
		table.add_column("Signed",    justify="center")
		for c in contracts:
			signed_str = "[green]Yes[/green]" if c.is_signed else "[red]No[/red]"
			table.add_row(
				str(c.id), str(c.client_id), c.sales_contact,
				f"{c.total_amount:.2f} €", f"{c.remaining_amount:.2f} €", signed_str
			)
		console.print(table)

	# ------------------------------------------------------------------
	# List
	# ------------------------------------------------------------------

	def list_all_contracts(self) -> None:
		self._render_contracts(self.controller.get_all_contracts(), "All Contracts")

	def list_unsigned_contracts(self) -> None:
		self._render_contracts(self.controller.get_unsigned_contracts(), "Unsigned Contracts")

	def list_unpaid_contracts(self) -> None:
		self._render_contracts(self.controller.get_unpaid_contracts(), "Unpaid Contracts")

	# ------------------------------------------------------------------
	# Create
	# ------------------------------------------------------------------

	def create_contract(self) -> None:
		console.print("\n[bold cyan]=== Create Contract ===[/bold cyan]")
		client_id         = click.prompt("Client ID", type=int)
		total_amount      = click.prompt("Total amount", type=float)
		remaining_str     = click.prompt("Remaining amount (leave blank = total)", default="", show_default=False)

		remaining_amount = float(remaining_str) if remaining_str else total_amount

		contract = self.controller.create_contract({
			"client_id":        client_id,
			"total_amount":     total_amount,
			"remaining_amount": remaining_amount,
		})
		console.print(f"[green]✔ Contract created:[/green] #{contract.id} — {contract.total_amount:.2f} € (signed: {contract.is_signed})")

	# ------------------------------------------------------------------
	# Update  (all fields, including relational: client_id, sales_contact)
	# ------------------------------------------------------------------

	def update_contract(self) -> None:
		console.print("\n[bold cyan]=== Update Contract ===[/bold cyan]")
		contract_id      = click.prompt("Contract ID", type=int)
		total_str        = click.prompt("Total amount      (leave blank to keep)", default="", show_default=False)
		remaining_str    = click.prompt("Remaining amount  (leave blank to keep)", default="", show_default=False)
		signed_str       = click.prompt("Signed? (y/n)     (leave blank to keep)", default="", show_default=False)
		sales_contact    = click.prompt("Sales contact     (leave blank to keep)", default="", show_default=False)
		client_id_str    = click.prompt("Client ID         (leave blank to keep)", default="", show_default=False)

		update_data = {}
		if total_str:       update_data["total_amount"]     = float(total_str)
		if remaining_str:   update_data["remaining_amount"] = float(remaining_str)
		if signed_str in {"y", "n"}: update_data["is_signed"] = signed_str == "y"
		if sales_contact:   update_data["sales_contact"]    = sales_contact
		if client_id_str:   update_data["client_id"]        = int(client_id_str)

		if not update_data:
			console.print("[yellow]Nothing to update.[/yellow]")
			return

		contract = self.controller.update_contract(contract_id, update_data)
		console.print(f"[green]✔ Contract updated:[/green] #{contract.id} — signed: {contract.is_signed}, remaining: {contract.remaining_amount:.2f} €")

	# ------------------------------------------------------------------
	# Sign
	# ------------------------------------------------------------------

	def sign_contract(self) -> None:
		console.print("\n[bold cyan]=== Sign Contract ===[/bold cyan]")
		contract_id = click.prompt("Contract ID", type=int)
		contract = self.controller.sign_contract(contract_id)
		console.print(f"[green]✔ Contract #{contract.id} is now signed.[/green]")
