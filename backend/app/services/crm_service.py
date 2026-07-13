from sqlalchemy.orm import Session
from app.repositories.hcp import hcp as hcp_repo
from app.repositories.product import product as product_repo
from app.repositories.interaction import interaction as interaction_repo
from app.schemas.schemas import InteractionCreate, HCPResponse, ProductResponse, HCPBase
from fastapi import HTTPException

class CRMService:
    @staticmethod
    def create_hcp(db: Session, obj_in: HCPBase):
        return hcp_repo.create(db, obj_in=obj_in.model_dump())

    @staticmethod
    def search_hcps(db: Session, query: str):
        if not query:
            return []
        return hcp_repo.search_by_name(db, query=query)

    @staticmethod
    def search_products(db: Session, query: str):
        if not query:
            return []
        return product_repo.search_by_name(db, query=query)

    @staticmethod
    def create_interaction(db: Session, obj_in: InteractionCreate):
        # Validate HCP exists
        hcp = hcp_repo.get(db, id=obj_in.hcp_id)
        if not hcp:
            raise HTTPException(status_code=404, detail="HCP not found")
        
        # Validate all products exist
        for prod_id in obj_in.product_ids:
            if not product_repo.get(db, id=prod_id):
                raise HTTPException(status_code=404, detail=f"Product {prod_id} not found")

        # Convert schemas to dicts
        interaction_dict = obj_in.model_dump(exclude={"product_ids", "follow_ups"})
        follow_ups_list = [fu.model_dump() for fu in obj_in.follow_ups]
        
        interaction = interaction_repo.create_with_followups_and_products(
            db=db,
            obj_in=interaction_dict,
            product_ids=obj_in.product_ids,
            follow_ups=follow_ups_list
        )
        return interaction

crm_service = CRMService()
