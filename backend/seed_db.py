import os
import sys

# Ensure backend directory is in sys.path
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BACKEND_DIR)

from app_v2_secure import create_app, db
from app.models.models import User

app = create_app()

from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()
    # Check if admin exists
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            username="admin", 
            email="admin@finwise.local", 
            role="admin",
            password_hash=generate_password_hash("admin")
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user created (admin / admin)")
    else:
        admin.password_hash = generate_password_hash("admin")
        db.session.commit()
        print("Admin user updated (admin / admin)")
