from sqlalchemy.orm import Session
from app.repositories.base import CRUDBase
from app.models.models import Interaction, FollowUp
from typing import Dict, Any, List
from uuid import UUID

class CRUDInteraction(CRUDBase[Interaction]):
    def create_with_followups_and_products(self, db: Session, *, obj_in: Dict[str, Any], product_ids: List[UUID], follow_ups: List[Dict[str, Any]]) -> Interaction:
        db_obj = Interaction(
            hcp_id=obj_in["hcp_id"],
            interaction_date=obj_in["interaction_date"],
            sentiment=obj_in.get("sentiment"),
            summary=obj_in.get("summary"),
            status=obj_in.get("status", "COMPLETED")
        )
        
        # Link products
        # Requires fetching product models, but usually just creating the association table entries works.
        # SQLAlchemy requires mapping or direct relationship handling.
        db.add(db_obj)
        db.flush() # flush to get the UUID for followups and products
        
        # Assuming we handle products via API/Services, but simple manual link here for seed
        for product_id in product_ids:
            from app.models.models import InteractionProduct
            db.execute(
                InteractionProduct.__table__.insert().values(
                    interaction_id=db_obj.id,
                    product_id=product_id
                )
            )

        for fu in follow_ups:
            fu_obj = FollowUp(
                interaction_id=db_obj.id,
                action_item=fu["action_item"],
                priority=fu["priority"],
                due_date=fu.get("due_date"),
                reason=fu.get("reason"),
                status=fu.get("status", "PENDING")
            )
            db.add(fu_obj)

        db.commit()
        db.refresh(db_obj)
        return db_obj

interaction = CRUDInteraction(Interaction)
