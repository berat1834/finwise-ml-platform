from flask import Blueprint

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
credit_bp = Blueprint('credit', __name__, url_prefix='/credit')
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
compliance_bp = Blueprint('compliance', __name__, url_prefix='/compliance')
health_bp = Blueprint('health', __name__, url_prefix='/health')
