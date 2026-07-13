from typing import List
from sqlalchemy.orm import Session
from app.repositories.base import CRUDBase
from app.models.models import Product

class CRUDProduct(CRUDBase[Product]):
    def search_by_name(self, db: Session, *, query: str) -> List[Product]:
        search = f"%{query}%"
        return db.query(self.model).filter(self.model.name.ilike(search)).all()

product = CRUDProduct(Product)
