
import sentry_sdk
from models.user import Department, User
from sqlalchemy.orm import Session
from utils.permissions import check_permission, require_auth

class UserController:
	def __init__(self, db_session: Session, auth_controller):
		self.db_session = db_session
		self.auth_controller = auth_controller

	@check_permission(Department.GESTION.value)
	def create_user(self, user_data):
		user = User(**user_data)
		self.db_session.add(user)
		self.db_session.commit()
		self.db_session.refresh(user)
		sentry_sdk.capture_message(
			f"Collaborator created: id={user.id}, employee_number={user.employee_number}, department={user.department}",
			level="info",
		)
		return user

	@check_permission(Department.GESTION.value)
	def update_user(self, user_id, update_data):
		user = self.db_session.query(User).filter(User.id == user_id).first()
		if not user:
			raise ValueError("User not found.")
		for key, value in update_data.items():
			setattr(user, key, value)
		self.db_session.commit()
		self.db_session.refresh(user)
		sentry_sdk.capture_message(
			f"Collaborator updated: id={user.id}, employee_number={user.employee_number}, fields={list(update_data.keys())}",
			level="info",
		)
		return user

	@check_permission(Department.GESTION.value)
	def delete_user(self, user_id):
		user = self.db_session.query(User).filter(User.id == user_id).first()
		if not user:
			raise ValueError("User not found.")
		self.db_session.delete(user)
		self.db_session.commit()
		return True

	@require_auth
	def get_user_by_id(self, user_id):
		"""
		Retrieve a user by their ID.
		"""
		return self.db_session.query(User).filter(User.id == user_id).first()

	@require_auth
	def get_users_by_department(self, department):
		"""
		Retrieve users filtered by department.
		"""
		return self.db_session.query(User).filter(User.department == department).all()

	@require_auth
	def get_all_users(self):
		"""
		Retrieve all users.
		"""
		return self.db_session.query(User).all()