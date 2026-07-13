import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal, engine
from app.models.models import Base, HCP, Product
from app.repositories.hcp import hcp as hcp_repo
from app.repositories.product import product as product_repo
from datetime import datetime, timezone

def seed_db():
    print("Starting seed...")
    db = SessionLocal()
    try:
        # Check if already seeded
        if hcp_repo.get_multi(db, limit=1):
            print("Database already seeded.")
            return

        print("Seeding HCPs...")
        hcp1 = hcp_repo.create(db, obj_in={
            "first_name": "Rajiv",
            "last_name": "Sharma",
            "specialty": "Cardiology",
            "email": "dr.sharma@example.com"
        })
        hcp2 = hcp_repo.create(db, obj_in={
            "first_name": "Anita",
            "last_name": "Desai",
            "specialty": "General Practice",
            "email": "dr.desai@example.com"
        })

        print("Seeding Products...")
        product1 = product_repo.create(db, obj_in={
            "name": "CardioPlus",
            "therapeutic_area": "Cardiovascular"
        })
        product2 = product_repo.create(db, obj_in={
            "name": "NeuroMax",
            "therapeutic_area": "Neurology"
        })

        print("Seed completed successfully.")
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
