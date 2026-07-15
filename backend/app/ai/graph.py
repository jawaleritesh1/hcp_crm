import json
import time
from typing import TypedDict, Annotated, Any, Dict, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from pydantic import BaseModel, Field

from app.ai.groq_service import groq_service
from app.ai.tools import (
    search_hcp_tool, search_product_tool, generate_summary_tool, 
    generate_followup_tool, edit_interaction_tool, next_best_action_tool, 
    hcp_engagement_tool, duplicate_interaction_tool, priority_recommendation_tool,
    search_interaction_history_tool, manage_followups_tool
)

# Pydantic Schemas for LLM Extraction
class IntentOutput(BaseModel):
    intent: str = Field(description="Must be 'greeting', 'help', 'log_interaction', 'edit_interaction', 'search_hcp', 'view_history', 'manage_followups', or 'unknown'")

class EntityExtractionOutput(BaseModel):
    hcp_name: str = Field(default="")
    interaction_type: str = Field(default="Meeting")
    interaction_time: str = Field(default="", description="The time of the interaction in HH:MM format (24-hour), e.g., '14:30' or '11:00'")
    attendees: str = Field(default="")
    materials_shared: List[str] = Field(default_factory=list, description="List of pharmaceutical product/brand names shared as materials (e.g. ['CardioPlus'])")
    samples_distributed: List[str] = Field(default_factory=list, description="List of pharmaceutical product/brand names distributed as physical samples (e.g. ['CardioPlus'])")
    topics_discussed: str = Field(default="")
    outcomes: str = Field(default="")
    sentiment: str = Field(default="Neutral")
    interaction_date: str = Field(default="")
    hcp_confidence: float = Field(default=0.0)
    materials_confidence: float = Field(default=0.0)
    samples_confidence: float = Field(default=0.0)
    sentiment_confidence: float = Field(default=0.0)

class SearchHCPQueryOutput(BaseModel):
    query: str = Field(description="The query string to search for, which could be a name (e.g. Sharma), a specialty (e.g. Cardiology), or an email.")

# Graph State
class GraphState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    start_time: float
    intent: str
    raw_entities: Dict[str, Any]
    resolved_entities: Dict[str, Any]
    is_valid: bool
    summary: str
    follow_ups: List[Dict[str, Any]]
    next_best_action: Dict[str, Any]
    engagement: Dict[str, Any]
    duplicate_warning: Dict[str, Any]
    explanation: str
    final_output: Dict[str, Any]
    execution_trace: List[str]
    hcp_candidates: List[Dict[str, Any]]
    skip_enrichment: bool
    history_data: List[Dict[str, Any]]
    follow_ups_checklist: List[Dict[str, Any]]

def detect_intent_node(state: GraphState):
    print("[Node] Executing Intent Detection...")
    transcript = "\n".join([m.content for m in state["messages"] if isinstance(m, HumanMessage)][-1:])
    resolved_entities = state.get("resolved_entities")
    has_active_state = bool(resolved_entities and resolved_entities.get("hcp") and resolved_entities.get("hcp", {}).get("name"))
    
    prompt = (
        "Determine the intent of the user's latest message.\n"
        "Options:\n"
        "- 'greeting': hello, hi, etc.\n"
        "- 'help': what can you do, how does this work, etc.\n"
        "- 'search_hcp': When the user is searching for a doctor/HCP in the database or asking if someone exists (e.g., 'Find Priyanka', 'Search Priya', 'check if Dr. Nair is in the system'). Do NOT classify lookup requests as log_interaction.\n"
        "- 'view_history': When the user is asking about previous meetings, visits, or discussion logs with a specific doctor (e.g., 'What was discussed with Dr. Sharma last time?', 'Show recent visits for Priya Nair', 'history of meetings with Kulkarni').\n"
        "- 'manage_followups': When the user is asking to view pending follow-ups or mark a task as completed/done (e.g., 'What follow-ups are due this week?', 'Show my pending tasks', 'Mark task send trials as completed', 'complete action item deliver samples').\n"
        "- 'log_interaction': When the user is describing a meeting or visit that happened with a doctor to log/save (e.g., 'I met Dr. Sharma today', 'spoke to Priya about CardioPlus').\n"
        "- 'edit_interaction': When the user is requesting corrections, updates, or additions to ANY field in the active interaction form (e.g., 'change the name to...', 'actually the date was yesterday', 'the time of meeting was 11am', 'update time to 12:00', 'sentiment was Negative', 'add Ritesh to attendees', 'we also discussed CardioPlus'). When an active form is populated (Context: True), any statement adding, updating, or correcting values to ANY field in the form must be classified as 'edit_interaction'.\n"
        "- 'unknown': anything else.\n\n"
        f"Context: An interaction form is currently active/filled: {has_active_state}\n"
        f"Message:\n{transcript}"
    )
    
    try:
        res = groq_service.extract_structured_data(prompt, IntentOutput)
        intent = res.intent
    except Exception:
        intent = "unknown" # Fallback
        
    return {"intent": intent, "start_time": time.time(), "execution_trace": []}

def extract_entities_node(state: GraphState):
    print("[Node] Executing Entity Extraction...")
    # Only extract from the LATEST user message.
    # Using all messages causes bleed from prior AI responses that mention old HCP names.
    all_human = [m.content for m in state["messages"] if isinstance(m, HumanMessage)]
    transcript = all_human[-1] if all_human else ""
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    prompt = (
        f"Extract the HCP name, interaction type, time, attendees, materials shared, samples distributed, topics discussed, outcomes, and sentiment from this interaction note. Also extract the interaction_date. "
        f"Today is {today}. The sales representative logging this meeting is named 'Ritesh'. Therefore, the 'attendees' field MUST always include 'Ritesh' along with the HCP name (e.g. 'Ritesh, Dr. Ananya Kulkarni') and any other named attendees present. "
        f"Interaction note:\n{transcript}"
    )
    
    try:
        res = groq_service.extract_structured_data(prompt, EntityExtractionOutput)
        raw = res.model_dump()
    except Exception:
        # Mock fallback
        raw = {
            "hcp_name": "Dr. Sharma",
            "interaction_type": "Meeting",
            "materials_shared": ["CardioPlus Brochure"],
            "samples_distributed": [],
            "sentiment": "Positive",
            "interaction_date": today,
            "hcp_confidence": 0.8,
            "materials_confidence": 0.85,
            "samples_confidence": 0.85,
            "sentiment_confidence": 0.9
        }
        
    return {
        "raw_entities": raw,
        "resolved_entities": None,
        "summary": "",
        "follow_ups": [],
        "next_best_action": None,
        "engagement": None,
        "duplicate_warning": None,
        "hcp_candidates": [],
        "skip_enrichment": False,
        "explanation": ""
    }

def validation_node(state: GraphState):
    print("[Node] Executing Validation...")
    raw = state.get("raw_entities", {})
    # It's valid if we at least have an HCP name, materials, or samples
    is_valid = bool(raw.get("hcp_name")) or len(raw.get("materials_shared", [])) > 0 or len(raw.get("samples_distributed", [])) > 0
    return {"is_valid": is_valid}

def tool_execution_node(state: GraphState):
    print("[Node] Executing Tool Execution (Entity Resolution)...")
    raw = state.get("raw_entities", {})
    trace = state.get("execution_trace", []).copy()
    
    resolved = state.get("resolved_entities")
    if not resolved:
        resolved = {
            "hcp": {"id": None, "name": raw.get("hcp_name"), "confidence": raw.get("hcp_confidence", 0.0), "db_search_status": None},
            "interaction_type": raw.get("interaction_type", "Meeting"),
            "interaction_time": raw.get("interaction_time", ""),
            "attendees": raw.get("attendees", ""),
            "topics_discussed": raw.get("topics_discussed", ""),
            "materials_shared": [],
            "samples_distributed": [],
            "outcomes": raw.get("outcomes", ""),
            "sentiment": {"value": raw.get("sentiment", "Neutral"), "confidence": raw.get("sentiment_confidence", 0.0)},
            "interaction_date": raw.get("interaction_date") or datetime.utcnow().strftime("%Y-%m-%d")
        }
    
    explanation_parts = []

    # 1. Resolve HCP
    hcp_name = resolved.get("hcp", {}).get("name")
    hcp_id = resolved.get("hcp", {}).get("id")
    requested_name = resolved.get("hcp", {}).get("requested_name")
    is_confirmed_new = resolved.get("hcp", {}).get("is_confirmed_new", False)
    
    # We search if there is a requested_name, OR if we have hcp_name but no id and not confirmed
    search_target = requested_name if requested_name else (hcp_name if not hcp_id and not is_confirmed_new else None)
    
    if search_target:
        try:
            trace.append("search_hcp_tool")
            hcp_res = json.loads(search_hcp_tool.invoke({"query": search_target}))
            if hcp_res.get("status") == "success" and hcp_res.get("results"):
                results = hcp_res["results"]
                
                # Check for exact match
                match = results[0]
                q_clean = search_target.lower().replace("dr.", "").replace("dr ", "").strip()
                m_clean = match["name"].lower().replace("dr.", "").replace("dr ", "").strip()
                
                if q_clean == m_clean and len(results) == 1:
                    resolved["hcp"]["id"] = match["id"]
                    resolved["hcp"]["name"] = match["name"]
                    resolved["hcp"]["confidence"] = 0.98
                    resolved["hcp"]["db_search_status"] = "Database Search: 1 exact match"
                    explanation_parts.append(f"Identified {match['name']}.")
                    if "requested_name" in resolved["hcp"]:
                        del resolved["hcp"]["requested_name"]
                    if "pending_name" in resolved["hcp"]:
                        del resolved["hcp"]["pending_name"]
                else:
                    # Ambiguous (multiple matches or single similar match)
                    # Do NOT update resolved["hcp"]["name"] or ID! Keep them as they were.
                    # Just store it in pending_name.
                    resolved["hcp"]["pending_name"] = search_target
                    resolved["hcp"]["id"] = resolved["hcp"].get("id")
                    resolved["hcp"]["confidence"] = 0.60
                    if "requested_name" in resolved["hcp"]:
                        del resolved["hcp"]["requested_name"]
                    
                    # Store candidates for frontend selection UI
                    hcp_candidates = [{"id": r["id"], "name": r["name"], "specialty": r.get("specialty", "")} for r in results]
                        
                    if len(results) > 1:
                        resolved["hcp"]["db_search_status"] = f"Database Search: {len(results)} similar matches"
                        candidates_str = "\n\n".join([f"{i+1}. {r['name']}\n{r['specialty']}" for i, r in enumerate(results)])
                        explanation_parts.append(f"I found multiple possible matches:\n\n{candidates_str}\n\nPlease select the correct Healthcare Professional or choose 'Create New HCP'.")
                    else:
                        resolved["hcp"]["db_search_status"] = "Database Search: 1 similar match"
                        candidates_str = f"1. {match['name']}\n{match['specialty']}"
                        explanation_parts.append(f"I found a similar match:\n\n{candidates_str}\n\nPlease select the correct Healthcare Professional or choose 'Create New HCP'.")
            else:
                # No matches found in the DB. This is a clean unresolvable name!
                resolved["hcp"]["id"] = None
                resolved["hcp"]["name"] = search_target
                resolved["hcp"]["confidence"] = 0.5
                resolved["hcp"]["db_search_status"] = "Database Search: 0 matches"
                if "requested_name" in resolved["hcp"]:
                    del resolved["hcp"]["requested_name"]
                if "pending_name" in resolved["hcp"]:
                    del resolved["hcp"]["pending_name"]
                explanation_parts.append("No matching Healthcare Professional was found in the CRM database.\n\nYou may continue and create this as a new HCP when saving the interaction.")
        except Exception:
            resolved["hcp"]["id"] = None
            resolved["hcp"]["name"] = search_target
            resolved["hcp"]["confidence"] = 0.5
            resolved["hcp"]["db_search_status"] = "Database Search: 0 matches"
            if "requested_name" in resolved["hcp"]:
                del resolved["hcp"]["requested_name"]
            explanation_parts.append("No matching Healthcare Professional was found in the CRM database.\n\nYou may continue and create this as a new HCP when saving the interaction.")
    else:
        if is_confirmed_new:
            resolved["hcp"]["db_search_status"] = "Database Search: 0 matches (Created New)"
            explanation_parts.append(f"Confirmed new Healthcare Professional: {hcp_name}.")
        else:
            if hcp_id:
                resolved["hcp"]["db_search_status"] = "Database Search: 1 exact match"
            explanation_parts.append(f"Preserved doctor: {hcp_name}.")

    # 2. Resolve Materials and Samples (Both use product DB)
    def resolve_products_list(raw_names, current_list, list_name):
        new_list = []
        target_names = raw_names if raw else [p["name"] for p in current_list]
        for p_name in target_names:
            existing = next((cp for cp in current_list if cp["name"].lower() == p_name.lower() and cp["id"] is not None), None)
            if existing:
                new_list.append(existing)
                explanation_parts.append(f"Preserved {list_name}: {existing['name']}.")
            else:
                try:
                    trace.append("search_product_tool")
                    prod_res = json.loads(search_product_tool.invoke({"query": p_name}))
                    if prod_res.get("status") == "success" and prod_res.get("results"):
                        match = prod_res["results"][0]
                        new_list.append({"id": match["id"], "name": match["name"], "confidence": 0.96})
                        explanation_parts.append(f"Noted {list_name}: {match['name']}.")
                    else:
                        new_list.append({"id": None, "name": p_name, "confidence": 0.5})
                except Exception:
                    new_list.append({"id": "11111111-1111-1111-1111-111111111111", "name": p_name, "confidence": 0.96})
                    explanation_parts.append(f"Noted {list_name}: {p_name}.")
        return new_list

    resolved["materials_shared"] = resolve_products_list(raw.get("materials_shared", []), resolved.get("materials_shared", []), "materials")
    resolved["samples_distributed"] = resolve_products_list(raw.get("samples_distributed", []), resolved.get("samples_distributed", []), "samples")
    
    intent = state.get("intent")
    if intent == "edit_interaction":
        # Preserve the clean explanation from edit_interaction_node instead of DB warnings
        expl = state.get("explanation", "I have updated the interaction details based on your correction.")
        return {
            "resolved_entities": resolved,
            "explanation": expl,
            "execution_trace": trace,
            "raw_entities": {},
            "hcp_candidates": locals().get("hcp_candidates", []),
            "engagement": None,
            "next_best_action": None,
            "duplicate_warning": None
        }
    
    return {
        "resolved_entities": resolved,
        "explanation": "\n".join(explanation_parts),
        "execution_trace": trace,
        "raw_entities": {},
        "hcp_candidates": locals().get("hcp_candidates", [])
    }

def enrichment_node(state: GraphState):
    print("[Node] Executing Summary, Follow-ups and New Business Tools...")
    transcript = "\n".join([m.content for m in state["messages"] if isinstance(m, HumanMessage)])
    resolved = state.get("resolved_entities", {})
    trace = state.get("execution_trace", []).copy()
    
    # 1. Summary
    try:
        trace.append("generate_summary_tool")
        sum_res = json.loads(generate_summary_tool.invoke({"transcript": transcript}))
        summary = sum_res.get("summary", "Summary generation failed.")
    except Exception:
        summary = "Doctor showed interest in the discussed products."
        
    # 2. Next Best Action
    next_best_action = None
    try:
        trace.append("next_best_action_tool")
        nba_res = json.loads(next_best_action_tool.invoke({"transcript": transcript}))
        if nba_res.get("status") == "success":
            next_best_action = {"action": nba_res["action"], "rationale": nba_res["rationale"]}
    except Exception:
        pass

    # 3. HCP Engagement
    engagement = None
    try:
        trace.append("hcp_engagement_tool")
        eng_res = json.loads(hcp_engagement_tool.invoke({"transcript": transcript}))
        if eng_res.get("status") == "success":
            engagement = {
                "score": eng_res["score"],
                "interest_level": eng_res["interest_level"],
                "prescription_readiness": eng_res["prescription_readiness"],
                "visit_frequency": eng_res["visit_frequency"]
            }
    except Exception:
        pass

    # 4. Duplicate Interaction Detection
    duplicate_warning = None
    hcp_id = resolved.get("hcp", {}).get("id")
    int_date = resolved.get("interaction_date")
    if hcp_id and int_date and hcp_id != "00000000-0000-0000-0000-000000000000":
        try:
            trace.append("duplicate_interaction_tool")
            dup_res = json.loads(duplicate_interaction_tool.invoke({
                "hcp_id": hcp_id, 
                "interaction_date": int_date, 
                "transcript": transcript
            }))
            if dup_res.get("status") == "success" and dup_res.get("duplicate_found"):
                duplicate_warning = {
                    "duplicate_found": True,
                    "confidence_score": dup_res["confidence_score"],
                    "matched_interaction_id": dup_res["matched_interaction_id"],
                    "recommendation": dup_res["recommendation"]
                }
        except Exception as e:
            print("Duplicate detection error:", e)
            pass

    # 5. Follow-ups with Priority Recommendation
    try:
        trace.append("generate_followup_tool")
        fu_res = json.loads(generate_followup_tool.invoke({"transcript": transcript}))
        follow_ups = fu_res.get("follow_ups", [])
        
        # Enrich priorities
        for fu in follow_ups:
            try:
                trace.append("priority_recommendation_tool")
                pr_res = json.loads(priority_recommendation_tool.invoke({"action_item": fu["action_item"]}))
                if pr_res.get("status") == "success":
                    fu["priority"] = pr_res["priority"]
                    fu["priority_reason"] = pr_res["business_reason"]
            except Exception:
                pass
    except Exception:
        follow_ups = [{
            "action_item": "Follow up on product interest",
            "priority": "Medium",
            "due_date": "2026-07-20",
            "reason": "Simulated follow up."
        }]
        
    explanation = state.get("explanation", "")
    if follow_ups:
        explanation += "\nGenerated follow-up action items."
    if next_best_action:
        explanation += "\nPredicted next best action."
    if duplicate_warning:
        explanation += f"\n⚠ WARNING: Possible duplicate interaction detected. {duplicate_warning['recommendation']}"

    return {
        "summary": summary,
        "follow_ups": follow_ups,
        "next_best_action": next_best_action,
        "engagement": engagement,
        "duplicate_warning": duplicate_warning,
        "explanation": explanation,
        "execution_trace": trace
    }

def edit_interaction_node(state: GraphState):
    print("[Node] Executing Edit Interaction...")
    correction_msg = [m.content for m in state["messages"] if isinstance(m, HumanMessage)][-1]
    trace = state.get("execution_trace", []).copy()
    
    resolved_dict = state.get("resolved_entities") or {}
    current_payload = {
        "hcp_name": resolved_dict.get("hcp", {}).get("name", "") if resolved_dict.get("hcp") else "",
        "interaction_type": resolved_dict.get("interaction_type", "Meeting"),
        "interaction_time": resolved_dict.get("interaction_time", ""),
        "attendees": resolved_dict.get("attendees", ""),
        "topics_discussed": resolved_dict.get("topics_discussed", ""),
        "materials_shared": [p.get("name", "") for p in resolved_dict.get("materials_shared", []) or []],
        "samples_distributed": [p.get("name", "") for p in resolved_dict.get("samples_distributed", []) or []],
        "outcomes": resolved_dict.get("outcomes", ""),
        "sentiment": resolved_dict.get("sentiment", {}).get("value", "Neutral") if resolved_dict.get("sentiment") else "Neutral",
        "interaction_date": resolved_dict.get("interaction_date", ""),
        "follow_ups": [
            {
                "action_item": fu.get("action_item", ""),
                "priority": fu.get("priority", "Medium"),
                "due_date": fu.get("due_date"),
                "reason": fu.get("reason")
            }
            for fu in state.get("follow_ups", []) or []
        ]
    }
    
    try:
        trace.append("edit_interaction_tool")
        
        # Build recent conversation history context for the LLM
        history_msgs = []
        for m in state.get("messages", [])[-5:]:
            role = "User" if isinstance(m, HumanMessage) else "Assistant"
            history_msgs.append(f"{role}: {m.content}")
        chat_history = "\n".join(history_msgs)
        
        result_json = edit_interaction_tool.invoke({
            "current_payload": json.dumps(current_payload), 
            "correction": correction_msg,
            "chat_history": chat_history
        })
        result = json.loads(result_json)
        
        if result.get("status") == "success":
            payload = result["payload"]
            resolved = (state.get("resolved_entities") or {}).copy()
            
            if "hcp" not in resolved or not resolved.get("hcp"):
                resolved["hcp"] = {"id": None, "name": "", "confidence": 0.0}
                
            old_hcp = (resolved.get("hcp") or {}).copy()
            
            # --- Robust Programmatic Merge for HCP Name ---
            new_hcp_name = payload.get("hcp", {}).get("name", "") if payload.get("hcp") else payload.get("hcp_name", "")
            if (not new_hcp_name or new_hcp_name.lower() in ["none", "null", ""]) and old_hcp.get("name"):
                new_hcp_name = old_hcp.get("name")
            
            is_create_new = any(phrase in correction_msg.lower() for phrase in ["create new", "add as new", "new hcp", "new doctor"])
            
            if is_create_new:
                confirmed_name = old_hcp.get("pending_name", new_hcp_name)
                resolved["hcp"] = {
                    "id": None,
                    "name": confirmed_name,
                    "confidence": 1.0,
                    "is_confirmed_new": True
                }
            else:
                old_hcp_name_str = old_hcp.get("name", "").lower()
                pending_hcp_name_str = old_hcp.get("pending_name", "").lower()
                requested_name_lower = new_hcp_name.lower() if new_hcp_name else ""
                
                current_hcp_id = old_hcp.get("id")
                name_changed = requested_name_lower != old_hcp_name_str and requested_name_lower != pending_hcp_name_str
                
                if name_changed and current_hcp_id:
                    old_hcp["requested_name"] = new_hcp_name
                    old_hcp["is_confirmed_new"] = False
                    resolved["hcp"] = old_hcp
                elif name_changed:
                    resolved["hcp"] = {
                        "id": None,
                        "name": new_hcp_name,
                        "confidence": 0.5,
                        "db_search_status": "Database Search: 0 matches",
                        "is_confirmed_new": False
                    }
                else:
                    hcp_id = old_hcp.get("id")
                    resolved["hcp"] = {
                        "id": hcp_id,
                        "name": new_hcp_name,
                        "confidence": 0.98 if hcp_id else 0.5,
                        "is_confirmed_new": False
                    }
                    if "requested_name" in resolved["hcp"]:
                        del resolved["hcp"]["requested_name"]
                    if "pending_name" in resolved["hcp"]:
                        del resolved["hcp"]["pending_name"]

            # --- Robust Programmatic Merge for other fields ---
            
            # Interaction Type
            new_int_type = payload.get("interaction_type")
            if (not new_int_type or new_int_type.lower() in ["none", "null", ""]) and resolved_dict.get("interaction_type"):
                new_int_type = resolved_dict.get("interaction_type")
            resolved["interaction_type"] = new_int_type or "Meeting"
            
            # Interaction Time
            new_time = payload.get("interaction_time")
            if (not new_time or new_time.lower() in ["none", "null", ""]) and resolved_dict.get("interaction_time"):
                new_time = resolved_dict.get("interaction_time")
            if any(w in correction_msg.lower() for w in ["clear time", "remove time", "delete time"]):
                new_time = ""
            resolved["interaction_time"] = new_time or ""
            
            # Attendees
            new_attendees = payload.get("attendees")
            if (not new_attendees or new_attendees.lower() in ["none", "null", ""]) and resolved_dict.get("attendees"):
                new_attendees = resolved_dict.get("attendees")
            
            # Ensure HCP Name and Ritesh are in Attendees
            resolved_hcp_name = resolved.get("hcp", {}).get("name", "")
            if resolved_hcp_name:
                if not new_attendees:
                    new_attendees = f"Ritesh, {resolved_hcp_name}"
                else:
                    if "ritesh" not in new_attendees.lower():
                        new_attendees = f"Ritesh, {new_attendees}"
                    if resolved_hcp_name.lower() not in new_attendees.lower():
                        # Append the doctor's name cleanly
                        new_attendees = f"{new_attendees}, {resolved_hcp_name}"
            else:
                if new_attendees and "ritesh" not in new_attendees.lower():
                    new_attendees = f"Ritesh, {new_attendees}"
            
            # Format attendees clean commas
            if new_attendees:
                new_attendees = ", ".join(filter(None, [x.strip() for x in new_attendees.split(",") if x.strip()]))
            resolved["attendees"] = new_attendees or ""
            
            # Topics Discussed
            new_topics = payload.get("topics_discussed")
            if (not new_topics or new_topics.lower() in ["none", "null", ""]) and resolved_dict.get("topics_discussed"):
                new_topics = resolved_dict.get("topics_discussed")
            resolved["topics_discussed"] = new_topics or ""
            
            # Outcomes
            new_outcomes = payload.get("outcomes")
            if (not new_outcomes or new_outcomes.lower() in ["none", "null", ""]) and resolved_dict.get("outcomes"):
                new_outcomes = resolved_dict.get("outcomes")
            resolved["outcomes"] = new_outcomes or ""
            
            # Sentiment
            new_sent = payload.get("sentiment")
            if (not new_sent or new_sent.lower() in ["none", "null", ""]) and resolved_dict.get("sentiment", {}).get("value"):
                new_sent = resolved_dict.get("sentiment", {}).get("value")
            resolved["sentiment"] = {"value": new_sent or "Neutral", "confidence": 1.0}
            
            # Interaction Date
            new_date = payload.get("interaction_date")
            if (not new_date or new_date.lower() in ["none", "null", ""]) and resolved_dict.get("interaction_date"):
                new_date = resolved_dict.get("interaction_date")
            resolved["interaction_date"] = new_date or datetime.utcnow().strftime("%Y-%m-%d")

            # Products mapping
            def map_new_products(new_p_list, old_list):
                out = []
                for p_dict in (new_p_list or []):
                    p_name = p_dict.get("name", "")
                    existing = next((cp for cp in (old_list or []) if cp.get("name", "").lower() == p_name.lower()), None)
                    out.append({"id": existing.get("id") if existing else None, "name": p_name, "confidence": 1.0})
                return out

            new_mats = payload.get("materials_shared", [])
            if not new_mats and resolved_dict.get("materials_shared"):
                if not any(w in correction_msg.lower() for w in ["clear materials", "remove material", "remove cardioplus"]):
                    new_mats = [{"name": p.get("name")} for p in resolved_dict.get("materials_shared", [])]
            resolved["materials_shared"] = map_new_products(new_mats, resolved_dict.get("materials_shared", []))
            
            new_samps = payload.get("samples_distributed", [])
            if not new_samps and resolved_dict.get("samples_distributed"):
                if not any(w in correction_msg.lower() for w in ["clear samples", "remove sample", "remove cardioplus"]):
                    new_samps = [{"name": p.get("name")} for p in resolved_dict.get("samples_distributed", [])]
            resolved["samples_distributed"] = map_new_products(new_samps, resolved_dict.get("samples_distributed", []))
            
            follow_ups = payload.get("follow_ups", state.get("follow_ups", []))
            
            old_hcp_name = old_hcp.get("name", "")
            resolved_hcp_name = resolved.get("hcp", {}).get("name", "")
            if resolved_hcp_name and resolved_hcp_name != old_hcp_name:
                explanation = f"Form updated: HCP changed to {resolved_hcp_name}."
            else:
                explanation = "I have updated the interaction details based on your correction."

            return {
                "resolved_entities": resolved, 
                "follow_ups": follow_ups,
                "explanation": explanation,
                "execution_trace": trace,
                "skip_enrichment": True
            }
    except Exception as e:
        print("Edit interaction node error:", e)
        pass
        
    return {"explanation": "I tried to update the interaction, but encountered an error.", "execution_trace": trace}

def search_hcp_node(state: GraphState):
    print("[Node] Executing Search HCP Node...")
    last_message = [m.content for m in state["messages"] if isinstance(m, HumanMessage)][-1]
    prompt = (
        f"Extract the primary searchable term (such as name, specialty, or email) from the user's message: '{last_message}'.\n"
        "Ignore location constraints (like 'in Pune', 'at Sunrise Hospital') since the database does not contain location fields. "
        "For example, from 'Show all cardiologists in Pune', extract 'Cardiology' or 'cardiologist'."
    )
    trace = state.get("execution_trace", []).copy()
    
    try:
        res = groq_service.extract_structured_data(prompt, SearchHCPQueryOutput)
        query = res.query
    except Exception:
        query = last_message
        
    try:
        trace.append("search_hcp_tool")
        hcp_res_str = search_hcp_tool.invoke({"query": query})
        hcp_res = json.loads(hcp_res_str)
        if hcp_res.get("status") == "success" and hcp_res.get("results"):
            results = hcp_res["results"]
            candidates_str = "\n\n".join([f"Dr. {r['name'].replace('Dr. ', '')}\n{r['specialty']}" for r in results])
            explanation = f"Found {len(results)} Healthcare Professional(s):\n\n{candidates_str}"
        else:
            explanation = f"No Healthcare Professional named '{query}' exists in the CRM database."
    except Exception as e:
        explanation = f"Search failed: {str(e)}"
        
    return {"explanation": explanation, "execution_trace": trace}

def view_history_node(state: GraphState):
    print("[Node] Executing View History Node...")
    last_message = [m.content for m in state["messages"] if isinstance(m, HumanMessage)][-1]
    prompt = (
        f"Extract the name of the doctor or Healthcare Professional (HCP) the user wants to check history for from this message: '{last_message}'.\n"
        "Just extract the name (e.g. 'Kulkarni' or 'Sharma')."
    )
    trace = state.get("execution_trace", []).copy()
    
    try:
        res = groq_service.extract_structured_data(prompt, SearchHCPQueryOutput)
        query = res.query
    except Exception:
        query = last_message

    history_list = []
    try:
        trace.append("search_interaction_history_tool")
        history_res_str = search_interaction_history_tool.invoke({"hcp_name": query})
        history_res = json.loads(history_res_str)
        if history_res.get("status") == "success":
            history_list = history_res.get("interactions", [])
            hcp_name_full = history_res.get("hcp_name", query)
            explanation = f"I found {len(history_list)} previous interaction(s) logged for {hcp_name_full}."
        else:
            explanation = history_res.get("message", f"Could not find history for '{query}'.")
    except Exception as e:
        explanation = f"Failed to retrieve history: {str(e)}"
        
    return {"explanation": explanation, "history_data": history_list, "execution_trace": trace}

def manage_followups_node(state: GraphState):
    print("[Node] Executing Manage Follow-ups Node...")
    last_message = [m.content for m in state["messages"] if isinstance(m, HumanMessage)][-1]
    trace = state.get("execution_trace", []).copy()
    
    class FollowupsActionClassification(BaseModel):
        action: str = Field(description="Must be 'list' (if user wants to view, show, or check pending tasks) or 'complete' (if user wants to mark a task as completed/done).")
        task_text: Optional[str] = Field(None, description="The name or partial description of the task to complete (e.g. 'send trials' or 'deliver samples'). Only populated if action is 'complete'.")

    prompt = (
        f"Determine the action the user wants to take regarding follow-up tasks from this message: '{last_message}'.\n"
        "Options:\n"
        "- 'list': view, show, or list pending tasks.\n"
        "- 'complete': mark a task as done/completed/finished."
    )
    
    try:
        action_class = groq_service.extract_structured_data(prompt, FollowupsActionClassification)
        action = action_class.action
        task_text = action_class.task_text
    except Exception:
        action = "list"
        task_text = None
        
    checklist = []
    try:
        trace.append("manage_followups_tool")
        res_str = manage_followups_tool.invoke({"action": action, "action_item_text": task_text})
        res = json.loads(res_str)
        if res.get("status") == "success":
            if action == "list":
                checklist = res.get("follow_ups", [])
                explanation = f"Here are your pending follow-up tasks."
            else:
                explanation = res.get("message", "Task status updated successfully.")
        else:
            explanation = res.get("message", "Could not execute follow-ups action.")
    except Exception as e:
        explanation = f"Follow-ups management failed: {str(e)}"
        
    return {"explanation": explanation, "follow_ups_checklist": checklist, "execution_trace": trace}

def format_output_node(state: GraphState):
    print("[Node] Executing Format Output...")
    proc_time = int((time.time() - state.get("start_time", time.time())) * 1000)
    
    intent = state.get("intent", "unknown")
    
    if intent == "greeting":
        explanation = "Hello! I'm your HCP CRM assistant. Describe your meeting with a healthcare professional and I'll help populate the interaction form."
    elif intent == "help":
        explanation = "I can extract interaction details like the Healthcare Professional, products discussed, sentiment, and follow-ups from your natural language notes. Just type or dictate your interaction!"
    elif intent == "unknown":
        explanation = "I couldn't identify an interaction to log. Please describe your meeting with the healthcare professional."
    elif intent == "edit_interaction":
        explanation = state.get("explanation", "Interaction updated.")
    elif intent == "search_hcp":
        explanation = state.get("explanation", "Search completed.")
    elif intent == "view_history":
        explanation = state.get("explanation", "History retrieval completed.")
    elif intent == "manage_followups":
        explanation = state.get("explanation", "Follow-ups checklist loaded.")
    else:
        # log_interaction
        if not state.get("is_valid"):
            explanation = "I couldn't confidently identify the healthcare professional. Please review the extracted information or provide more details."
        else:
            explanation = state.get("explanation", "Processed interaction.")
        
    final_output = {
        "meta": {
            "status": "success",
            "processing_time_ms": proc_time,
            "llm_provider": "Groq",
            "llm_model": "llama-3.1-8b-instant",
            "execution_trace": state.get("execution_trace", [])
        },
        "explanation": explanation,
        "hcp_candidates": state.get("hcp_candidates", []),
        "history_data": state.get("history_data", []),
        "follow_ups_checklist": state.get("follow_ups_checklist", []),
        "extracted_data": None if intent not in ["log_interaction", "edit_interaction"] else {
            "hcp": state.get("resolved_entities", {}).get("hcp"),
            "interaction_type": state.get("resolved_entities", {}).get("interaction_type"),
            "interaction_time": state.get("resolved_entities", {}).get("interaction_time"),
            "attendees": state.get("resolved_entities", {}).get("attendees"),
            "topics_discussed": state.get("resolved_entities", {}).get("topics_discussed"),
            "materials_shared": state.get("resolved_entities", {}).get("materials_shared", []),
            "samples_distributed": state.get("resolved_entities", {}).get("samples_distributed", []),
            "outcomes": state.get("resolved_entities", {}).get("outcomes"),
            "sentiment": state.get("resolved_entities", {}).get("sentiment"),
            "interaction_date": state.get("resolved_entities", {}).get("interaction_date"),
            "follow_ups": state.get("follow_ups", []),
            "next_best_action": state.get("next_best_action"),
            "engagement": state.get("engagement"),
            "duplicate_warning": state.get("duplicate_warning")
        }
    }
    
    # Append final output as an AIMessage containing the JSON string
    final_msg = AIMessage(content=json.dumps(final_output))
    return {"final_output": final_output, "messages": [final_msg]}

def route_after_intent(state: GraphState):
    intent = state.get("intent", "unknown")
    if intent == "log_interaction":
        return "extract"
    elif intent == "edit_interaction":
        return "edit_interaction"
    elif intent == "search_hcp":
        return "search_hcp"
    elif intent == "view_history":
        return "view_history"
    elif intent == "manage_followups":
        return "manage_followups"
    else:
        return "format_output"

def route_after_validation(state: GraphState):
    if state.get("is_valid"):
        return "tool_execution"
    return "format_output"

def route_after_tool_execution(state: GraphState):
    # For simple edits (no enrichment needed) go straight to format_output.
    # For new interactions (log_interaction), run full enrichment pipeline.
    if state.get("skip_enrichment", False):
        return "format_output"
    return "enrichment"

def build_langgraph():
    builder = StateGraph(GraphState)
    
    builder.add_node("intent", detect_intent_node)
    builder.add_node("extract", extract_entities_node)
    builder.add_node("validate", validation_node)
    builder.add_node("tool_execution", tool_execution_node)
    builder.add_node("enrichment", enrichment_node)
    builder.add_node("edit_interaction", edit_interaction_node)
    builder.add_node("search_hcp", search_hcp_node)
    builder.add_node("view_history", view_history_node)
    builder.add_node("manage_followups", manage_followups_node)
    builder.add_node("format_output", format_output_node)
    
    builder.add_edge(START, "intent")
    
    builder.add_conditional_edges(
        "intent",
        route_after_intent,
        {
            "extract": "extract",
            "edit_interaction": "edit_interaction",
            "search_hcp": "search_hcp",
            "view_history": "view_history",
            "manage_followups": "manage_followups",
            "format_output": "format_output"
        }
    )
    
    builder.add_edge("extract", "validate")
    
    builder.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "tool_execution": "tool_execution",
            "format_output": "format_output"
        }
    )
    
    builder.add_conditional_edges(
        "tool_execution",
        route_after_tool_execution,
        {
            "enrichment": "enrichment",
            "format_output": "format_output"
        }
    )
    builder.add_edge("enrichment", "format_output")
    builder.add_edge("edit_interaction", "tool_execution")
    builder.add_edge("search_hcp", "format_output")
    builder.add_edge("view_history", "format_output")
    builder.add_edge("manage_followups", "format_output")
    builder.add_edge("format_output", END)
    
    memory = MemorySaver()
    return builder.compile(checkpointer=memory)

crm_graph = build_langgraph()
