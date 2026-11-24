import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import engine, Base, SessionLocal
from app.models import User, UserRole
from app.services.auth_service import hash_password


def init_database():
    print("Creating all database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

    db = SessionLocal()
    try:
        # Seed default Admin
        admin = db.query(User).filter(User.email == "admin@docuflow.com").first()
        if not admin:
            admin = User(
                name="System Administrator",
                email="admin@docuflow.com",
                password_hash=hash_password("Admin@123456"),
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin)
            print("Seeded default Admin: admin@docuflow.com (Admin@123456)")

        # Seed default Processing Manager
        manager = db.query(User).filter(User.email == "manager@docuflow.com").first()
        if not manager:
            manager = User(
                name="Processing Manager",
                email="manager@docuflow.com",
                password_hash=hash_password("Manager@123456"),
                role=UserRole.PROCESSING_MANAGER,
                is_active=True
            )
            db.add(manager)
            print("Seeded default Manager: manager@docuflow.com (Manager@123456)")

        # Seed default Viewer
        viewer = db.query(User).filter(User.email == "viewer@docuflow.com").first()
        if not viewer:
            viewer = User(
                name="Document Viewer",
                email="viewer@docuflow.com",
                password_hash=hash_password("Viewer@123456"),
                role=UserRole.VIEWER,
                is_active=True
            )
            db.add(viewer)
            print("Seeded default Viewer: viewer@docuflow.com (Viewer@123456)")

        db.commit()
        print("Default accounts initialized successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error during database initialization: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
