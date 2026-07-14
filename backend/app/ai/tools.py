from langchain_core.tools import tool
from typing import List, Optional
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
    interaction_type: Optional[str] = Field(description="E.g., Meeting, Phone Call, Email")
    interaction_time: Optional[str] = Field(description="Time of the interaction in HH:MM format")
    attendees: Optional[str] = Field(description="Names of people attending")
    materials_shared: List[str] = Field(description="List of presentation or printed materials shared")
    samples_distributed: List[str] = Field(description="List of physical product samples distributed")
    topics_discussed: Optional[str] = Field(description="Key topics discussed")
    outcomes: Optional[str] = Field(description="Key outcomes or agreements")
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
        prompt = (
            f"Extract the HCP name, interaction type, time, attendees, materials shared, samples distributed, topics discussed, outcomes, overall sentiment, and interaction date from this interaction: {transcript}.\n"
            f"Today's date is {today}. "
            "The sales representative logging this meeting is named 'Ritesh'. Therefore, the 'attendees' field MUST always include 'Ritesh' along with the HCP name (e.g. 'Ritesh, Dr. Ananya Kulkarni') and any other named attendees present."
        )
        result = groq_service.extract_structured_data(prompt, LogInteractionPayload)
        
        payload = {
            "hcp": {"name": result.hcp_name},
            "interaction_type": result.interaction_type,
            "interaction_time": result.interaction_time,
            "attendees": result.attendees,
            "topics_discussed": result.topics_discussed,
            "materials_shared": [{"name": p} for p in result.materials_shared],
            "samples_distributed": [{"name": p} for p in result.samples_distributed],
            "outcomes": result.outcomes,
            "sentiment": result.sentiment,
            "interaction_date": result.interaction_date
        }
        return json.dumps({"status": "success", "payload": payload})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Interaction preparation failed: {str(e)}"})

# ----------------------------------------------------
# 6. Edit Interaction Tool (Transformation Only)
# ----------------------------------------------------
class ExtractedFollowUpPayload(BaseModel):
    action_item: str
    priority: str
    due_date: Optional[str] = None
    reason: Optional[str] = None

class FullInteractionPayload(BaseModel):
    hcp_name: str
    interaction_type: Optional[str]
    interaction_time: Optional[str] = Field(description="The time of the interaction in HH:MM format (24-hour), e.g., '14:30' or '11:00'")
    attendees: Optional[str]
    topics_discussed: Optional[str]
    materials_shared: List[str]
    samples_distributed: List[str]
    outcomes: Optional[str]
    sentiment: str = Field(description="Positive, Neutral, or Negative")
    interaction_date: str = Field(description="The date of the interaction in YYYY-MM-DD format")
    follow_ups: List[ExtractedFollowUpPayload] = Field(default_factory=list)

class EditInteractionInput(BaseModel):
    current_payload: str = Field(..., description="The JSON string of the current interaction payload.")
    correction: str = Field(..., description="The user's natural language instruction for how to correct the payload.")
    chat_history: Optional[str] = Field(None, description="The recent conversation history to resolve choices (e.g. Choose 1) or context.")

@tool("edit_interaction_tool", args_schema=EditInteractionInput, return_direct=False)
def edit_interaction_tool(current_payload: str, correction: str, chat_history: Optional[str] = None) -> str:
    """
    Applies user corrections to an existing interaction payload.
    DOES NOT update the database. Returns the updated JSON payload.
    """
    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        history_context = f"Conversation Context (very important to resolve ambiguous requests like 'Choose 1' or 'Create new HCP'):\n{chat_history}\n\n" if chat_history else ""
        prompt = (
            f"You are a strict CRM merging tool. You receive a current JSON payload representing the state of an interaction:\n"
            f"{current_payload}\n\n"
            f"{history_context}"
            f"A user wants to apply the following correction: '{correction}'\n"
            f"Apply the correction exactly as requested. Today is {today}.\n"
            f"CRITICAL RULES:\n"
            f"1. Perform a TRUE merge. Preserve all existing fields, values, materials, samples, sentiment, outcomes, and follow-up items UNLESS the correction explicitly asks to change them.\n"
            f"2. Modify ONLY the requested fields.\n"
            f"3. Never erase or overwrite unrelated information.\n"
            f"4. If a date is changed, format it as YYYY-MM-DD.\n"
            f"5. Return the full, updated payload conforming to the FullInteractionPayload schema.\n"
            f"6. TYPE CONSTRAINTS: 'materials_shared' and 'samples_distributed' must be flat lists of strings (e.g. [\"CardioPlus\"]), NOT list of dicts. 'sentiment' must be a single string (e.g. \"Positive\"), NOT a dict.\n"
            f"7. The sales representative logging this meeting is named 'Ritesh'. Therefore, the 'attendees' field MUST always include 'Ritesh' along with the HCP name (e.g. 'Ritesh, Dr. Ananya Kulkarni') and any other named attendees present."
        )
        result = groq_service.extract_structured_data(prompt, FullInteractionPayload)
        
        updated_payload = {
            "hcp": {"name": result.hcp_name},
            "interaction_type": result.interaction_type,
            "interaction_time": result.interaction_time,
            "attendees": result.attendees,
            "topics_discussed": result.topics_discussed,
            "materials_shared": [{"name": p} for p in result.materials_shared],
            "samples_distributed": [{"name": p} for p in result.samples_distributed],
            "outcomes": result.outcomes,
            "sentiment": result.sentiment,
            "interaction_date": result.interaction_date,
            "follow_ups": [fu.model_dump() for fu in result.follow_ups]
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
        prompt = (
            f"Analyze the interaction transcript to determine the Next Best Action for the sales rep: {transcript}\n"
            f"CRITICAL RECOMMENDATION RULES:\n"
            f"1. Recommending action MUST be dynamic and tailored to the context (e.g. doctor interest, products discussed, sentiment, materials/samples requested, objections raised).\n"
            f"2. DO NOT return generic static recommendations.\n"
            f"3. Output a concrete actionable step (e.g., 'Send latest clinical evidence', 'Deliver requested samples', 'Schedule revisit after 14 days', 'Arrange product presentation') and a business rationale justifying it."
        )
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
        prompt = (
            f"Analyze this interaction transcript and calculate engagement metrics: {transcript}\n"
            f"CRITICAL SCORING RUBRIC:\n"
            f"1. Base score (0-100) must be dynamically calculated based on:\n"
            f"   - Overall sentiment (Positive = +30, Neutral = +15, Negative = 0)\n"
            f"   - Interest in products discussed (High = +20, Medium = +10, Low = 0)\n"
            f"   - Objections raised (Objections = -15, No objections = +10)\n"
            f"   - Action requests: requested samples (+15), requested literature/evidence (+15)\n"
            f"   - Commitments: agreed to revisit or follow-up (+15)\n"
            f"2. Ensure the Engagement Score is dynamic and calculated strictly according to these points. Never return a static score (like 80).\n"
            f"3. Return the quantitative details: score, interest_level (Low, Medium, High), prescription_readiness, and recommended visit frequency."
        )
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
            idate = i.interaction_date if isinstance(i.interaction_date, datetime) else datetime.strptime(str(i.interaction_date)[:10], "%Y-%m-%d")
            if start_date.date() <= idate.date() <= end_date.date():
                candidates.append({"id": str(i.id), "date": str(idate.date()), "summary": i.summary})
                
        if not candidates:
            return json.dumps({
                "status": "success", 
                "duplicate_found": False, 
                "confidence_score": 0.0, 
                "matched_interaction_id": None, 
                "recommendation": "No duplicate interaction detected."
            })
            
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
        prompt = (
            f"Determine the priority (Critical, High, Medium, Low) of this follow-up action: '{action_item}'\n"
            f"CRITICAL BUSINESS LOGIC RULES:\n"
            f"1. Assign 'Critical' if the doctor requires urgent safety or compliance resolution.\n"
            f"2. Assign 'High' if the doctor requested samples or clinical evidence/data/literature.\n"
            f"3. Assign 'Medium' if it is a standard follow-up schedule, a revisit request, or a general product question.\n"
            f"4. Assign 'Low' if there is no immediate action requested, or it is a routine login.\n"
            f"5. Provide a clear, short business reason justification for the assigned priority."
        )
        result = groq_service.extract_structured_data(prompt, PriorityRecommendationOutput)
        
        return json.dumps({
            "status": "success",
            "priority": result.priority,
            "confidence": result.confidence,
            "business_reason": result.business_reason
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

# ----------------------------------------------------
# 11. Search Interaction History Tool
# ----------------------------------------------------
class SearchInteractionHistoryInput(BaseModel):
    hcp_name: str = Field(..., description="The name or partial name of the Healthcare Professional to search history for.")

@tool("search_interaction_history_tool", args_schema=SearchInteractionHistoryInput, return_direct=False)
def search_interaction_history_tool(hcp_name: str) -> str:
    """Search the database for previous interactions logged with a specific HCP."""
    db = SessionLocal()
    try:
        clean_query = hcp_name.replace("Dr.", "").replace("Dr ", "").strip()
        hcps = crm_service.search_hcps(db, clean_query)
        if not hcps:
            words = clean_query.split()
            if len(words) > 1:
                hcps = crm_service.search_hcps(db, words[-1])
        
        if not hcps:
            return json.dumps({"status": "error", "message": f"No Healthcare Professional named '{hcp_name}' found."})
        
        hcp = hcps[0]
        interactions = crm_service.get_hcp_interactions(db, str(hcp.id))
        
        results = []
        for i in interactions:
            results.append({
                "id": str(i.id),
                "interaction_type": i.interaction_type,
                "interaction_date": i.interaction_date.strftime("%Y-%m-%d") if isinstance(i.interaction_date, datetime) else str(i.interaction_date)[:10],
                "interaction_time": i.interaction_time or "",
                "attendees": i.attendees or "",
                "topics_discussed": i.topics_discussed or "",
                "outcomes": i.outcomes or "",
                "sentiment": i.sentiment or "Neutral"
            })
            
        return json.dumps({
            "status": "success",
            "hcp_name": f"Dr. {hcp.first_name} {hcp.last_name}",
            "interactions": results
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": f"History search failed: {str(e)}"})
    finally:
        db.close()

# ----------------------------------------------------
# 12. Manage Follow-ups Tool
# ----------------------------------------------------
class ManageFollowupsInput(BaseModel):
    action: str = Field("list", description="Must be 'list' (to show pending tasks) or 'complete' (to mark a task as done).")
    action_item_text: Optional[str] = Field(None, description="The text of the follow-up task to mark as completed (e.g., 'send trials').")

@tool("manage_followups_tool", args_schema=ManageFollowupsInput, return_direct=False)
def manage_followups_tool(action: str, action_item_text: Optional[str] = None) -> str:
    """List pending follow-up action items or mark a follow-up item as completed in the database."""
    db = SessionLocal()
    try:
        if action == "list":
            items = crm_service.get_pending_follow_ups(db)
            results = []
            for item in items:
                hcp = item.interaction.hcp
                hcp_name = f"Dr. {hcp.first_name} {hcp.last_name}"
                results.append({
                    "id": str(item.id),
                    "action_item": item.action_item,
                    "priority": item.priority,
                    "due_date": item.due_date.strftime("%Y-%m-%d") if isinstance(item.due_date, datetime) else str(item.due_date)[:10] if item.due_date else "",
                    "reason": item.reason or "",
                    "status": item.status,
                    "hcp_name": hcp_name
                })
            return json.dumps({"status": "success", "action": "list", "follow_ups": results})
        
        elif action == "complete":
            if not action_item_text:
                return json.dumps({"status": "error", "message": "Task description text is required to complete a follow-up."})
            
            items = crm_service.get_pending_follow_ups(db)
            target = None
            for item in items:
                if action_item_text.lower() in item.action_item.lower():
                    target = item
                    break
            
            if not target:
                return json.dumps({"status": "error", "message": f"No pending follow-up task matches '{action_item_text}'."})
                
            crm_service.update_follow_up_status(db, str(target.id), "COMPLETED")
            return json.dumps({
                "status": "success",
                "action": "complete",
                "message": f"Marked task '{target.action_item}' as completed.",
                "follow_up_id": str(target.id)
            })
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Follow-ups action failed: {str(e)}"})
    finally:
        db.close()

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
    priority_recommendation_tool,
    search_interaction_history_tool,
    manage_followups_tool
]
