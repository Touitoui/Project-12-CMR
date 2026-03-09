from datetime import datetime, timezone
import click
from rich.console import Console
from rich.table import Table
from rich import box

from controllers.event_controller import EventController

console = Console()
DATE_FMT = "%Y-%m-%d %H:%M"


class EventView:
	def __init__(self, controller: EventController):
		self.controller = controller

	# ------------------------------------------------------------------
	# Shared table renderer
	# ------------------------------------------------------------------

	def _render_events(self, events, title: str) -> None:
		if not events:
			console.print(f"[yellow]No events found ({title}).[/yellow]")
			return
		table = Table(title=title, box=box.ROUNDED, highlight=True)
		table.add_column("ID",       style="dim",  justify="right")
		table.add_column("Contract", justify="right")
		table.add_column("Client",   style="bold")
		table.add_column("Title")
		table.add_column("Start")
		table.add_column("End")
		table.add_column("Location")
		table.add_column("Attendees", justify="right")
		table.add_column("Support",   style="cyan")
		for e in events:
			table.add_row(
				str(e.id),
				str(e.contract_id),
				e.client_name,
				e.title or "-",
				e.event_date_start.strftime(DATE_FMT) if e.event_date_start else "-",
				e.event_date_end.strftime(DATE_FMT)   if e.event_date_end   else "-",
				e.location or "-",
				str(e.attendees) if e.attendees else "-",
				e.support_contact or "[red]None[/red]",
			)
		console.print(table)

	# ------------------------------------------------------------------
	# List
	# ------------------------------------------------------------------

	def list_all_events(self) -> None:
		self._render_events(self.controller.get_all_events(), "All Events")

	def list_events_without_support(self) -> None:
		"""GESTION: events with no support contact assigned."""
		self._render_events(self.controller.get_events_without_support(), "Events Without Support")

	def list_my_events(self) -> None:
		"""SUPPORT: events assigned to the current user."""
		self._render_events(self.controller.get_my_events(), "My Events")

	# ------------------------------------------------------------------
	# Create
	# ------------------------------------------------------------------

	def create_event(self) -> None:
		console.print("\n[bold cyan]=== Create Event ===[/bold cyan]")
		contract_id     = click.prompt("Contract ID", type=int)
		client_name     = click.prompt("Client name")
		title           = click.prompt("Title (optional)",          default="", show_default=False) or None
		client_contact  = click.prompt("Client contact (optional)", default="", show_default=False) or None
		start_str       = click.prompt(f"Start datetime ({DATE_FMT})")
		end_str         = click.prompt(f"End datetime   ({DATE_FMT})")
		location        = click.prompt("Location (optional)",        default="", show_default=False) or None
		attendees_str   = click.prompt("Attendees (optional)",       default="", show_default=False)
		notes           = click.prompt("Notes (optional)",           default="", show_default=False) or None

		event = self.controller.create_event({
			"contract_id":      contract_id,
			"client_name":      client_name,
			"title":            title,
			"client_contact":   client_contact,
			"event_date_start": datetime.strptime(start_str, DATE_FMT),
			"event_date_end":   datetime.strptime(end_str,   DATE_FMT),
			"location":         location,
			"attendees":        int(attendees_str) if attendees_str else None,
			"notes":            notes,
		})
		console.print(f"[green]✔ Event created:[/green] #{event.id} — {event.client_name}")

	# ------------------------------------------------------------------
	# Assign support
	# ------------------------------------------------------------------

	def assign_event(self) -> None:
		console.print("\n[bold cyan]=== Assign Support to Event ===[/bold cyan]")
		event_id        = click.prompt("Event ID", type=int)
		support_contact = click.prompt("Support contact (employee number)")
		event = self.controller.assign_event(event_id, support_contact)
		console.print(f"[green]✔ Event #{event.id} assigned to support:[/green] {event.support_contact}")

	# ------------------------------------------------------------------
	# Update  (all fields, including relational: contract_id, support_contact)
	# GESTION: can assign/change support_contact on any event
	# SUPPORT: can update location, dates, attendees, notes on own events
	# ------------------------------------------------------------------

	def update_event(self) -> None:
		console.print("\n[bold cyan]=== Update Event ===[/bold cyan]")
		event_id         = click.prompt("Event ID", type=int)
		support_contact  = click.prompt("Support contact   (leave blank to keep)", default="", show_default=False)
		title            = click.prompt("Title             (leave blank to keep)", default="", show_default=False)
		client_contact   = click.prompt("Client contact    (leave blank to keep)", default="", show_default=False)
		start_str        = click.prompt(f"Start ({DATE_FMT}) (leave blank to keep)", default="", show_default=False)
		end_str          = click.prompt(f"End   ({DATE_FMT}) (leave blank to keep)", default="", show_default=False)
		location         = click.prompt("Location          (leave blank to keep)", default="", show_default=False)
		attendees_str    = click.prompt("Attendees         (leave blank to keep)", default="", show_default=False)
		notes            = click.prompt("Notes             (leave blank to keep)", default="", show_default=False)
		contract_id_str  = click.prompt("Contract ID       (leave blank to keep)", default="", show_default=False)

		update_data = {}
		if support_contact: update_data["support_contact"]  = support_contact
		if title:           update_data["title"]             = title
		if client_contact:  update_data["client_contact"]    = client_contact
		if start_str:       update_data["event_date_start"]  = datetime.strptime(start_str, DATE_FMT)
		if end_str:         update_data["event_date_end"]    = datetime.strptime(end_str,   DATE_FMT)
		if location:        update_data["location"]          = location
		if attendees_str:   update_data["attendees"]         = int(attendees_str)
		if notes:           update_data["notes"]             = notes
		if contract_id_str: update_data["contract_id"]       = int(contract_id_str)

		if not update_data:
			console.print("[yellow]Nothing to update.[/yellow]")
			return

		event = self.controller.update_event(event_id, update_data)
		console.print(f"[green]✔ Event updated:[/green] #{event.id} — {event.client_name} (support: {event.support_contact or 'none'})")
