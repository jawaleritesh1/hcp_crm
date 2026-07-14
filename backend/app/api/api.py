from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.schemas import HCPResponse, ProductResponse, InteractionCreate, InteractionResponse, HCPBase
from app.services.crm_service import crm_service

api_router = APIRouter()

@api_router.post("/hcps", response_model=HCPResponse, status_code=201)
def create_hcp(
    hcp_in: HCPBase,
    db: Session = Depends(get_db)
):
    try:
        return crm_service.create_hcp(db, obj_in=hcp_in)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/hcps", response_model=List[HCPResponse])
def get_hcps(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    try:
        return crm_service.get_hcps(db, skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/hcps/search", response_model=List[HCPResponse])
def search_hcps(
    q: str = Query(..., min_length=1, description="Search query for HCP name"),
    db: Session = Depends(get_db)
):
    try:
        return crm_service.search_hcps(db, query=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/products/search", response_model=List[ProductResponse])
def search_products(
    q: str = Query(..., min_length=1, description="Search query for Product name"),
    db: Session = Depends(get_db)
):
    try:
        return crm_service.search_products(db, query=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/interactions", response_model=InteractionResponse, status_code=201)
def create_interaction(
    interaction_in: InteractionCreate,
    db: Session = Depends(get_db)
):
    return crm_service.create_interaction(db, obj_in=interaction_in)

from app.schemas.schemas import AIProcessRequest, AIProcessResponse
from app.ai.graph_service import graph_service

@api_router.post("/ai/process-interaction", response_model=AIProcessResponse)
def process_interaction(request: AIProcessRequest):
    try:
        result = graph_service.process_message(message=request.message, thread_id=request.thread_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
