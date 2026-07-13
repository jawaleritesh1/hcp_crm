from typing import List
from sqlalchemy.orm import Session
from app.repositories.base import CRUDBase
from app.models.models import HCP

class CRUDHCP(CRUDBase[HCP]):
    def search_by_name(self, db: Session, *, query: str) -> List[HCP]:
        search = f"%{query}%"
        return db.query(self.model).filter(
            (self.model.first_name.ilike(search)) | (self.model.last_name.ilike(search))
        ).all()

hcp = CRUDHCP(HCP)
