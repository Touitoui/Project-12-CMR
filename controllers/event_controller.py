
from models.event import Event
from models.contract import Contract
from models.user import Department, User
from sqlalchemy.orm import Session
from utils.permissions import check_permission, require_auth
from utils.token_manager import TokenManager

class EventController:
	def __init__(self, db_session: Session, auth_controller):
		self.db_session = db_session
		self.auth_controller = auth_controller

	@check_permission(Department.COMMERCIAL.value)
	def create_event(self, event_data):
		current_user = TokenManager.get_current_user()
		contract_id = event_data.get("contract_id")
		if not contract_id:
			raise ValueError("Contract ID is required to create an event.")
		contract = self.db_session.query(Contract).filter(Contract.id == contract_id).first()
		if not contract:
			raise ValueError("Contract not found.")
		if not contract.is_signed:
			raise PermissionError("Events can only be created for signed contracts.")
		if contract.sales_contact != current_user["employee_number"]:
			raise PermissionError("You can only create events for your own clients.")
		event = Event(**event_data)
		self.db_session.add(event)
		self.db_session.commit()
		self.db_session.refresh(event)
		return event

	@check_permission(Department.GESTION.value)
	def assign_event(self, event_id, support_contact):
		event = self.db_session.query(Event).filter(Event.id == event_id).first()
		if not event:
			raise ValueError("Event not found.")
		support_user = self.db_session.query(User).filter(User.employee_number == support_contact).first()
		if not support_user:
			raise ValueError(f"User with employee number '{support_contact}' does not exist.")
		if support_user.department != Department.SUPPORT:
			raise ValueError(f"User '{support_contact}' is not in the SUPPORT department.")
		event.support_contact = support_contact
		self.db_session.commit()
		self.db_session.refresh(event)
		return event

	@check_permission(Department.GESTION.value, Department.SUPPORT.value)
	def update_event(self, event_id, update_data):
		current_user = TokenManager.get_current_user()
		event = self.db_session.query(Event).filter(Event.id == event_id).first()
		if not event:
			raise ValueError("Event not found.")
		# SUPPORT can only update events they are responsible for
		if current_user["department"] == Department.SUPPORT.value:
			if event.support_contact != current_user["employee_number"]:
				raise PermissionError("You can only update events you are responsible for.")
		for key, value in update_data.items():
			setattr(event, key, value)
		self.db_session.commit()
		self.db_session.refresh(event)
		return event

	@check_permission(Department.GESTION.value)
	def delete_event(self, event_id):
		event = self.db_session.query(Event).filter(Event.id == event_id).first()
		if not event:
			raise ValueError("Event not found.")
		self.db_session.delete(event)
		self.db_session.commit()
		return True

	@require_auth
	def get_event_by_id(self, event_id):
		return self.db_session.query(Event).filter(Event.id == event_id).first()

	@require_auth
	def get_events_by_contract(self, contract_id):
		return self.db_session.query(Event).filter(Event.contract_id == contract_id).all()

	@require_auth
	def get_events_by_client(self, client_name):
		return self.db_session.query(Event).filter(Event.client_name == client_name).all()

	@require_auth
	def get_all_events(self):
		return self.db_session.query(Event).all()

	@check_permission(Department.GESTION.value)
	def get_events_without_support(self):
		"""Return events that have no support contact assigned (GESTION only)."""
		return self.db_session.query(Event).filter(
			(Event.support_contact == None) | (Event.support_contact == "")
		).all()

	@check_permission(Department.SUPPORT.value)
	def get_my_events(self):
		"""Return events assigned to the currently logged-in support user."""
		from utils.token_manager import TokenManager
		current_user = TokenManager.get_current_user()
		return self.db_session.query(Event).filter(
			Event.support_contact == current_user["employee_number"]
		).all()
