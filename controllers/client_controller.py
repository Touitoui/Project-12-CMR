from models.user import Department, User
from utils.permissions import check_permission, require_auth
from models.client import Client
from sqlalchemy.orm import Session

class ClientController:
	def __init__(self, db_session: Session, auth_controller):
		self.db_session = db_session
		self.auth_controller = auth_controller


	@check_permission(Department.COMMERCIAL.value)
	def create_client(self, client_data):
		current_user = self.auth_controller.get_current_user()
		client_data = dict(client_data)
		client_data["sales_contact"] = current_user["employee_number"]
		client = Client(**client_data)
		self.db_session.add(client)
		self.db_session.commit()
		self.db_session.refresh(client)
		return client


	@check_permission(Department.COMMERCIAL.value)
	def update_client(self, client_id, update_data):
		current_user = self.auth_controller.get_current_user()
		client = self.db_session.query(Client).filter(Client.id == client_id).first()
		if not client:
			raise ValueError("Client not found.")
		if client.sales_contact != current_user["employee_number"]:
			raise PermissionError("You can only update clients you are responsible for.")
		for key, value in update_data.items():
			setattr(client, key, value)
		self.db_session.commit()
		self.db_session.refresh(client)
		return client


	@check_permission(Department.COMMERCIAL.value)
	def delete_client(self, client_id):
		client = self.db_session.query(Client).filter(Client.id == client_id).first()
		if not client:
			raise ValueError("Client not found.")
		self.db_session.delete(client)
		self.db_session.commit()
		return True


	@require_auth
	def get_client_by_id(self, client_id):
		return self.db_session.query(Client).filter(Client.id == client_id).first()


	@require_auth
	def get_all_clients(self):
		return self.db_session.query(Client).all()

	@require_auth
	def get_all_clients_with_contacts(self):
		"""Return list of (client, user_or_none) with the sales contact resolved."""
		clients = self.db_session.query(Client).all()
		employee_numbers = {c.sales_contact for c in clients if c.sales_contact}
		users_by_empno = {
			u.employee_number: u
			for u in self.db_session.query(User).filter(
				User.employee_number.in_(employee_numbers)
			).all()
		}
		return [(c, users_by_empno.get(c.sales_contact)) for c in clients]
