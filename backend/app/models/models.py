import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

def get_utc_now():
    return datetime.now(timezone.utc)

class BaseModel(Base):
    __abstract__ = True
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

class HCP(BaseModel):
    __tablename__ = "hcp"
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    specialty = Column(String, nullable=False)
    email = Column(String, nullable=True, unique=True) # Added email per standard, making unique

    interactions = relationship("Interaction", back_populates="hcp")

    __table_args__ = (
        Index("ix_hcp_last_name", "last_name"),
    )

class Product(BaseModel):
    __tablename__ = "product"
    name = Column(String, nullable=False, unique=True)
    therapeutic_area = Column(String, nullable=False)

class InteractionProduct(Base):
    __tablename__ = "interaction_product"
    interaction_id = Column(Uuid(as_uuid=True), ForeignKey("interaction.id", ondelete="CASCADE"), primary_key=True)
    product_id = Column(Uuid(as_uuid=True), ForeignKey("product.id", ondelete="CASCADE"), primary_key=True)

class Interaction(BaseModel):
    __tablename__ = "interaction"
    hcp_id = Column(Uuid(as_uuid=True), ForeignKey("hcp.id", ondelete="RESTRICT"), nullable=False)
    interaction_type = Column(String, nullable=True)
    interaction_date = Column(DateTime(timezone=True), nullable=False)
    interaction_time = Column(String, nullable=True)
    attendees = Column(String, nullable=True)
    topics_discussed = Column(Text, nullable=True)
    outcomes = Column(Text, nullable=True)
    sentiment = Column(String, nullable=True)
    follow_ups_text = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="COMPLETED")

    hcp = relationship("HCP", back_populates="interactions")
    products = relationship("Product", secondary="interaction_product")
    follow_ups = relationship("FollowUp", back_populates="interaction", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_interaction_hcp_id", "hcp_id"),
        Index("ix_interaction_date", "interaction_date"),
    )

class FollowUp(BaseModel):
    __tablename__ = "follow_up"
    interaction_id = Column(Uuid(as_uuid=True), ForeignKey("interaction.id", ondelete="CASCADE"), nullable=False)
    action_item = Column(String, nullable=False)
    priority = Column(String, nullable=False) # High, Medium, Low
    due_date = Column(DateTime(timezone=True), nullable=True)
    reason = Column(Text, nullable=True)
    status = Column(String, default="PENDING")

    interaction = relationship("Interaction", back_populates="follow_ups")

    __table_args__ = (
        Index("ix_follow_up_interaction_id", "interaction_id"),
    )
