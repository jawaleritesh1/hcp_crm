from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

# HCP Schemas
class HCPBase(BaseModel):
    first_name: str
    last_name: str
    specialty: str
    email: Optional[str] = None

class HCPResponse(HCPBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Product Schemas
class ProductBase(BaseModel):
    name: str
    therapeutic_area: str

class ProductResponse(ProductBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# FollowUp Schemas
class FollowUpCreate(BaseModel):
    action_item: str
    priority: str = Field(pattern="^(High|Medium|Low)$")
    due_date: Optional[datetime] = None
    reason: Optional[str] = None

class FollowUpResponse(FollowUpCreate):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# AI Processing Schemas
class AIProcessRequest(BaseModel):
    message: str
    thread_id: str

class ConfidenceValue(BaseModel):
    value: str
    confidence: float

class EntityWithConfidence(BaseModel):
    id: Optional[str] = None
    name: str
    confidence: float

class NextBestAction(BaseModel):
    action: str
    rationale: str

class HCPEngagement(BaseModel):
    score: int
    interest_level: str
    prescription_readiness: str
    visit_frequency: str

class DuplicateWarning(BaseModel):
    duplicate_found: bool
    confidence_score: float
    matched_interaction_id: Optional[str] = None
    recommendation: Optional[str] = None

class ExtractedFollowUp(BaseModel):
    action_item: str
    priority: str
    priority_reason: Optional[str] = None
    due_date: Optional[str] = None
    reason: Optional[str] = None

class ExtractedData(BaseModel):
    hcp: Optional[EntityWithConfidence] = None
    products: List[EntityWithConfidence] = []
    sentiment: Optional[ConfidenceValue] = None
    summary: Optional[str] = None
    interaction_date: Optional[str] = None
    follow_ups: List[ExtractedFollowUp] = []
    next_best_action: Optional[NextBestAction] = None
    engagement: Optional[HCPEngagement] = None
    duplicate_warning: Optional[DuplicateWarning] = None

class MetaInfo(BaseModel):
    status: str
    processing_time_ms: int
    llm_provider: str
    llm_model: str

class AIProcessResponse(BaseModel):
    meta: MetaInfo
    explanation: str
    extracted_data: ExtractedData

# Interaction Schemas
class InteractionCreate(BaseModel):
    hcp_id: UUID
    interaction_date: datetime
    sentiment: Optional[str] = None
    summary: Optional[str] = None
    status: str = "COMPLETED"
    product_ids: List[UUID] = []
    follow_ups: List[FollowUpCreate] = []

class InteractionResponse(BaseModel):
    id: UUID
    hcp_id: UUID
    interaction_date: datetime
    sentiment: Optional[str]
    summary: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    products: List[ProductResponse] = []
    follow_ups: List[FollowUpResponse] = []

    class Config:
        from_attributes = True
