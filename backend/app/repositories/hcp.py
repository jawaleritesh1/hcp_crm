from typing import List
from sqlalchemy.orm import Session
from app.repositories.base import CRUDBase
from app.models.models import HCP

class CRUDHCP(CRUDBase[HCP]):
    def search_by_name(self, db: Session, *, query: str) -> List[HCP]:
        search = f"%{query}%"
        
        # Normalize common specialty variations (e.g. cardiologist -> cardiology)
        q_lower = query.lower().strip()
        if "cardiologist" in q_lower:
            q_lower = "cardiology"
        elif "pediatrician" in q_lower or "pediatricians" in q_lower:
            q_lower = "pediatrics"
        elif "dermatologist" in q_lower or "dermatologists" in q_lower:
            q_lower = "dermatology"
        elif "physician" in q_lower or "physicians" in q_lower:
            q_lower = "practice" # matches General Practice
            
        search_norm = f"%{q_lower}%"
        
        return db.query(self.model).filter(
            (self.model.first_name.ilike(search)) | 
            (self.model.last_name.ilike(search)) |
            ((self.model.first_name + " " + self.model.last_name).ilike(search)) |
            (self.model.specialty.ilike(search)) |
            (self.model.specialty.ilike(search_norm)) |
            (self.model.email.ilike(search))
        ).all()

hcp = CRUDHCP(HCP)
