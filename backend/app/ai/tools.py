from langchain_core.tools import tool
from typing import List
from pydantic import BaseModel, Field
import json
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.services.crm_service import crm_service
from app.ai.groq_service import groq_service, GroqServiceException

# ----------------------------------------------------
# 1. Search HCP Tool
# ----------------------------------------------------
class SearchHCPInput(BaseModel):
    query: str = Field(..., description="The name or partial name of the Healthcare Professional to search for.")

@tool("search_hcp_tool", args_schema=SearchHCPInput, return_direct=False)
def search_hcp_tool(query: str) -> str:
    """Search for a Healthcare Professional (HCP) by name to resolve their UUID."""
    db = SessionLocal()
    try:
        clean_query = query.replace("Dr.", "").replace("Dr ", "").strip()
        hcps = crm_service.search_hcps(db, clean_query)
        if not hcps:
            words = clean_query.split()
            if len(words) > 1:
                hcps = crm_service.search_hcps(db, words[-1])
        results = [{"id": str(h.id), "name": f"Dr. {h.first_name} {h.last_name}", "specialty": h.specialty} for h in hcps]
        return json.dumps({"status": "success", "results": results})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Database search failed: {str(e)}"})
    finally:
        db.close()

# ----------------------------------------------------
# 2. Search Product Tool
# ----------------------------------------------------
class SearchProductInput(BaseModel):
    query: str = Field(..., description="The name of the Pharmaceutical Product to search for.")

@tool("search_product_tool", args_schema=SearchProductInput, return_direct=False)
def search_product_tool(query: str) -> str:
    """Search for a Pharmaceutical Product by name to resolve its UUID."""
    db = SessionLocal()
    try:
        products = crm_service.search_products(db, query)
        results = [{"id": str(p.id), "name": p.name, "therapeutic_area": p.therapeutic_area} for p in products]
        return json.dumps({"status": "success", "results": results})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Database search failed: {str(e)}"})
    finally:
        db.close()

# ----------------------------------------------------
# 3. Generate Summary Tool
# ----------------------------------------------------
class SummaryOutput(BaseModel):
    summary: str

class GenerateSummaryInput(BaseModel):
    transcript: str = Field(..., description="The raw conversation transcript between the rep and the HCP.")

@tool("generate_summary_tool", args_schema=GenerateSummaryInput, return_direct=False)
def generate_summary_tool(transcript: str) -> str:
    """Generate a synthesized, professional interaction summary from raw context."""
    try:
        prompt = f"Please synthesize a professional CRM interaction summary based on this transcript: {transcript}"
        result = groq_service.extract_structured_data(prompt, SummaryOutput)
        return json.dumps({"status": "success", "summary": result.summary})
    except GroqServiceException as e:
        return json.dumps({"status": "error", "message": f"LLM generation failed: {str(e)}"})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Unexpected error: {str(e)}"})

# ----------------------------------------------------
# 4. Generate Follow-up Tool
# ----------------------------------------------------
class FollowUpItem(BaseModel):
    action_item: str
    priority: str = Field(description="High, Medium, or Low")
    reason: str
    due_date: str

class FollowUpOutput(BaseModel):
    follow_ups: List[FollowUpItem]

class GenerateFollowupInput(BaseModel):
    transcript: str = Field(..., description="The raw conversation transcript to extract action items from.")

@tool("generate_followup_tool", args_schema=GenerateFollowupInput, return_direct=False)
def generate_followup_tool(transcript: str) -> str:
    """Extract and generate structured follow-up action items from a conversation transcript."""
    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        prompt = f"Extract all promised or implied follow-up action items from this transcript: {transcript}. Today is {today}. Provide a concrete 'due_date' (YYYY-MM-DD) for each action item. If not specified, default to 7 days from today."
        result = groq_service.extract_structured_data(prompt, FollowUpOutput)
        
        formatted = []
        for fu in result.follow_ups:
            formatted.append({
                "action_item": fu.action_item,
                "priority": fu.priority,
                "due_date": fu.due_date,
                "reason": fu.reason
            })
            
        return json.dumps({"status": "success", "follow_ups": formatted})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"LLM follow-up extraction failed: {str(e)}"})

# ----------------------------------------------------
# 5. Log Interaction Tool (Preparation Only)
# ----------------------------------------------------
class LogInteractionPayload(BaseModel):
    hcp_name: str
    products: List[str]
    sentiment: str = Field(description="Positive, Neutral, or Negative")
    interaction_date: str = Field(description="The date of the interaction in YYYY-MM-DD format")

class LogInteractionInput(BaseModel):
    transcript: str = Field(..., description="The full conversation transcript to parse into an interaction payload.")

@tool("log_interaction_tool", args_schema=LogInteractionInput, return_direct=False)
def log_interaction_tool(transcript: str) -> str:
    """
    Parse a conversation transcript to prepare the interaction payload structure.
    DOES NOT save to the database. Returns a JSON structure ready for the frontend.
    """
    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        prompt = f"Extract the HCP name, products discussed, overall sentiment, and interaction date from this interaction: {transcript}. Today's date is {today}. If the interaction mentions 'yesterday', 'today', 'on 5 July', etc., resolve it to the exact YYYY-MM-DD date. If no date is mentioned, default to {today}."
        result = groq_service.extract_structured_data(prompt, LogInteractionPayload)
        
        payload = {
            "hcp": {"name": result.hcp_name},
            "products": [{"name": p} for p in result.products],
            "sentiment": result.sentiment,
            "interaction_date": result.interaction_date
        }
        return json.dumps({"status": "success", "payload": payload})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Interaction preparation failed: {str(e)}"})

# ----------------------------------------------------
# 6. Edit Interaction Tool (Transformation Only)
# ----------------------------------------------------
class EditInteractionInput(BaseModel):
    current_payload: str = Field(..., description="The JSON string of the current interaction payload.")
    correction: str = Field(..., description="The user's natural language instruction for how to correct the payload.")

@tool("edit_interaction_tool", args_schema=EditInteractionInput, return_direct=False)
def edit_interaction_tool(current_payload: str, correction: str) -> str:
    """
    Applies user corrections to an existing interaction payload.
    DOES NOT update the database. Returns the updated JSON payload.
    """
    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        prompt = f"Given this current interaction payload:\n{current_payload}\n\nApply this correction: '{correction}'\nOutput the fully updated payload. If the correction affects the date, resolve it to YYYY-MM-DD. Today is {today}."
        result = groq_service.extract_structured_data(prompt, LogInteractionPayload)
        
        updated_payload = {
            "hcp": {"name": result.hcp_name},
            "products": [{"name": p} for p in result.products],
            "sentiment": result.sentiment,
            "interaction_date": result.interaction_date
        }
        return json.dumps({"status": "success", "payload": updated_payload})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Interaction update failed: {str(e)}"})

# ----------------------------------------------------
# 7. Next Best Action Tool
# ----------------------------------------------------
class NextBestActionInput(BaseModel):
    transcript: str = Field(..., description="The raw conversation transcript")

@tool("next_best_action_tool", args_schema=NextBestActionInput, return_direct=False)
def next_best_action_tool(transcript: str) -> str:
    """Analyze the extracted interaction and recommend the next sales action."""
    try:
        from app.schemas.schemas import NextBestAction
        prompt = f"Analyze the interaction and recommend the next best sales action: {transcript}"
        result = groq_service.extract_structured_data(prompt, NextBestAction)
        return json.dumps({"status": "success", "action": result.action, "rationale": result.rationale})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

# ----------------------------------------------------
# 8. HCP Engagement Analysis Tool
# ----------------------------------------------------
class HCPEngagementInput(BaseModel):
    transcript: str = Field(..., description="The raw conversation transcript")

@tool("hcp_engagement_tool", args_schema=HCPEngagementInput, return_direct=False)
def hcp_engagement_tool(transcript: str) -> str:
    """Analyze the interaction and calculate engagement metrics."""
    try:
        from app.schemas.schemas import HCPEngagement
        prompt = f"Analyze this interaction and calculate Engagement Score (0-100), Interest Level (Low, Medium, High), Prescription Readiness, and Recommended Visit Frequency: {transcript}"
        result = groq_service.extract_structured_data(prompt, HCPEngagement)
        return json.dumps({
            "status": "success", 
            "score": result.score,
            "interest_level": result.interest_level,
            "prescription_readiness": result.prescription_readiness,
            "visit_frequency": result.visit_frequency
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

# ----------------------------------------------------
# 9. Duplicate Interaction Detection Tool
# ----------------------------------------------------
class DuplicateInteractionInput(BaseModel):
    hcp_id: str = Field(..., description="The UUID of the HCP")
    interaction_date: str = Field(..., description="The date of the interaction in YYYY-MM-DD format")
    transcript: str = Field(..., description="The conversation transcript")

@tool("duplicate_interaction_tool", args_schema=DuplicateInteractionInput, return_direct=False)
def duplicate_interaction_tool(hcp_id: str, interaction_date: str, transcript: str) -> str:
    """Compare the current interaction against previously logged interactions to detect duplicates."""
    db = SessionLocal()
    try:
        from app.repositories.interaction import interaction as interaction_repo
        from app.schemas.schemas import DuplicateWarning
        from datetime import datetime, timedelta
        
        target_date = datetime.strptime(interaction_date, "%Y-%m-%d")
        start_date = target_date - timedelta(days=7)
        end_date = target_date + timedelta(days=7)
        
        existing_interactions = db.query(interaction_repo.model).filter(
            interaction_repo.model.hcp_id == hcp_id
        ).all()
        
        candidates = []
        for i in existing_interactions:
            # interaction_date might be string or datetime in sqlite, ensure safe compare
            idate = i.interaction_date if isinstance(i.interaction_date, datetime) else datetime.strptime(str(i.interaction_date)[:10], "%Y-%m-%d")
            if start_date.date() <= idate.date() <= end_date.date():
                candidates.append({"id": str(i.id), "date": str(idate.date()), "summary": i.summary})
                
        if not candidates:
            return json.dumps({"status": "success", "duplicate_found": False, "confidence_score": 0.0, "matched_interaction_id": None, "recommendation": "No duplicates found"})
            
        candidates_str = json.dumps(candidates)
        prompt = f"Given these existing interactions for the HCP: {candidates_str}, compare them with this new interaction transcript: {transcript}. Is the new interaction likely a duplicate of one of the existing ones? Provide a duplicate_found boolean, a confidence score (0-1), the matched_interaction_id (if any), and a recommendation."
        
        result = groq_service.extract_structured_data(prompt, DuplicateWarning)
        
        return json.dumps({
            "status": "success",
            "duplicate_found": result.duplicate_found,
            "confidence_score": result.confidence_score,
            "matched_interaction_id": result.matched_interaction_id,
            "recommendation": result.recommendation
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        db.close()

# ----------------------------------------------------
# 10. Priority Recommendation Tool
# ----------------------------------------------------
class PriorityRecommendationInput(BaseModel):
    action_item: str = Field(..., description="The extracted follow-up action item")

class PriorityRecommendationOutput(BaseModel):
    priority: str
    confidence: float
    business_reason: str

@tool("priority_recommendation_tool", args_schema=PriorityRecommendationInput, return_direct=False)
def priority_recommendation_tool(action_item: str) -> str:
    """Determine the priority of follow-up actions using AI reasoning."""
    try:
        prompt = f"Determine the priority (Critical, High, Medium, Low) of this follow-up action: '{action_item}'. Provide the priority, a confidence score (0-1), and the business reason."
        result = groq_service.extract_structured_data(prompt, PriorityRecommendationOutput)
        
        return json.dumps({
            "status": "success",
            "priority": result.priority,
            "confidence": result.confidence,
            "business_reason": result.business_reason
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

TOOLS = [
    search_hcp_tool, 
    search_product_tool, 
    generate_summary_tool, 
    generate_followup_tool,
    log_interaction_tool,
    edit_interaction_tool,
    next_best_action_tool,
    hcp_engagement_tool,
    duplicate_interaction_tool,
    priority_recommendation_tool
]
