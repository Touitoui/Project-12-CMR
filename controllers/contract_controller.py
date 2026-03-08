import sentry_sdk
from models.contract import Contract
from models.client import Client
from models.user import Department
from sqlalchemy.orm import Session
from utils.permissions import check_permission, require_auth
from utils.token_manager import TokenManager

class ContractController:
	def __init__(self, db_session: Session, auth_controller):
		self.db_session = db_session
		self.auth_controller = auth_controller

	@check_permission(Department.COMMERCIAL.value, Department.GESTION.value)
	def create_contract(self, contract_data):
		current_user = TokenManager.get_current_user()
		client_id = contract_data.get("client_id")
		if not client_id:
			raise ValueError("Client ID is required to create a contract.")
		client = self.db_session.query(Client).filter(Client.id == client_id).first()
		if not client:
			raise ValueError("Client not found.")
		# COMMERCIAL can only create contracts for their own clients
		if current_user["department"] == Department.COMMERCIAL.value:
			if client.sales_contact != current_user["employee_number"]:
				raise PermissionError("You can only create contracts for your own clients.")
		contract_data = dict(contract_data)
		if "sales_contact" not in contract_data:
			contract_data["sales_contact"] = client.sales_contact
		contract_data["is_signed"] = False
		contract = Contract(**contract_data)
		self.db_session.add(contract)
		self.db_session.commit()
		self.db_session.refresh(contract)
		return contract

	@check_permission(Department.COMMERCIAL.value, Department.GESTION.value)
	def update_contract(self, contract_id, update_data):
		current_user = TokenManager.get_current_user()
		contract = self.db_session.query(Contract).filter(Contract.id == contract_id).first()
		if not contract:
			raise ValueError("Contract not found.")
		# COMMERCIAL can only update contracts they are responsible for
		if current_user["department"] == Department.COMMERCIAL.value:
			if contract.sales_contact != current_user["employee_number"]:
				raise PermissionError("You can only update contracts you are responsible for.")
		for key, value in update_data.items():
			setattr(contract, key, value)
		self.db_session.commit()
		self.db_session.refresh(contract)
		return contract

	@check_permission(Department.COMMERCIAL.value, Department.GESTION.value)
	def sign_contract(self, contract_id):
		current_user = TokenManager.get_current_user()
		contract = self.db_session.query(Contract).filter(Contract.id == contract_id).first()
		if not contract:
			raise ValueError("Contract not found.")
		if current_user["department"] == Department.COMMERCIAL.value:
			if contract.sales_contact != current_user["employee_number"]:
				raise PermissionError("You can only sign contracts you are responsible for.")
		contract.is_signed = True
		self.db_session.commit()
		self.db_session.refresh(contract)
		sentry_sdk.capture_message(
			f"Contract signed: id={contract.id}, client_id={contract.client_id}, sales_contact={contract.sales_contact}",
			level="info",
		)
		return contract

	@check_permission(Department.GESTION.value)
	def delete_contract(self, contract_id):
		contract = self.db_session.query(Contract).filter(Contract.id == contract_id).first()
		if not contract:
			raise ValueError("Contract not found.")
		self.db_session.delete(contract)
		self.db_session.commit()
		return True

	@require_auth
	def get_contract_by_id(self, contract_id):
		return self.db_session.query(Contract).filter(Contract.id == contract_id).first()

	@require_auth
	def get_all_contracts(self):
		return self.db_session.query(Contract).all()

	@require_auth
	def get_unsigned_contracts(self):
		return self.db_session.query(Contract).filter(Contract.is_signed.is_(False)).all()

	@require_auth
	def get_unpaid_contracts(self):
		return self.db_session.query(Contract).filter(Contract.remaining_amount > 0).all()