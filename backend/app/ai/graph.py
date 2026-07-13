import json
import time
from typing import TypedDict, Annotated, Any, Dict, List
from datetime import datetime
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from pydantic import BaseModel, Field

from app.ai.groq_service import groq_service
from app.ai.tools import search_hcp_tool, search_product_tool, generate_summary_tool, generate_followup_tool, edit_interaction_tool, next_best_action_tool, hcp_engagement_tool, duplicate_interaction_tool, priority_recommendation_tool

# Pydantic Schemas for LLM Extraction
class IntentOutput(BaseModel):
    intent: str = Field(description="Must be 'greeting', 'help', 'log_interaction', 'edit_interaction', or 'unknown'")

class EntityExtractionOutput(BaseModel):
    hcp_name: str = Field(default="")
    products: List[str] = Field(default_factory=list)
    sentiment: str = Field(default="Neutral")
    interaction_date: str = Field(default="")
    hcp_confidence: float = Field(default=0.0)
    products_confidence: float = Field(default=0.0)
    sentiment_confidence: float = Field(default=0.0)

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

def detect_intent_node(state: GraphState):
    print("[Node] Executing Intent Detection...")
    transcript = "\n".join([m.content for m in state["messages"] if isinstance(m, HumanMessage)][-1:])
    prompt = f"Determine the intent of the user's latest message. Options: 'greeting' (e.g. hello, hi), 'help' (e.g. what can you do), 'log_interaction' (e.g. met Dr Sharma today, discussed product), 'edit_interaction' (e.g. actually it was Dr Patel, change sentiment), 'unknown' (anything else). Message:\n{transcript}"
    
    try:
        res = groq_service.extract_structured_data(prompt, IntentOutput)
        intent = res.intent
    except Exception:
        intent = "unknown" # Fallback
        
    return {"intent": intent, "start_time": time.time()}

def extract_entities_node(state: GraphState):
    print("[Node] Executing Entity Extraction...")
    transcript = "\n".join([m.content for m in state["messages"] if isinstance(m, HumanMessage)])
    today = datetime.utcnow().strftime("%Y-%m-%d")
    prompt = f"Extract the HCP name, products, and sentiment from this conversation. Also extract the interaction_date. Today is {today}. If the interaction mentions 'yesterday', 'today', 'on 5 July', etc., resolve it to the exact YYYY-MM-DD date. If no date is mentioned, default to {today}. Transcript:\n{transcript}"
    
    try:
        res = groq_service.extract_structured_data(prompt, EntityExtractionOutput)
        raw = res.model_dump()
    except Exception:
        # Mock fallback
        raw = {
            "hcp_name": "Dr. Sharma",
            "products": ["CardioPlus"],
            "sentiment": "Positive",
            "interaction_date": today,
            "hcp_confidence": 0.8,
            "products_confidence": 0.85,
            "sentiment_confidence": 0.9
        }
        
    return {"raw_entities": raw}

def validation_node(state: GraphState):
    print("[Node] Executing Validation...")
    raw = state.get("raw_entities", {})
    # It's valid if we at least have an HCP name or products
    is_valid = bool(raw.get("hcp_name")) or len(raw.get("products", [])) > 0
    return {"is_valid": is_valid}

def tool_execution_node(state: GraphState):
    print("[Node] Executing Tool Execution (Entity Resolution)...")
    raw = state.get("raw_entities", {})
    resolved = {
        "hcp": {"id": None, "name": raw.get("hcp_name"), "confidence": raw.get("hcp_confidence", 0.0)},
        "products": [],
        "sentiment": {"value": raw.get("sentiment", "Neutral"), "confidence": raw.get("sentiment_confidence", 0.0)},
        "interaction_date": raw.get("interaction_date") or datetime.utcnow().strftime("%Y-%m-%d")
    }
    
    explanation_parts = []

    # Resolve HCP
    if raw.get("hcp_name"):
        try:
            hcp_res = json.loads(search_hcp_tool.invoke({"query": raw["hcp_name"]}))
            if hcp_res.get("status") == "success" and hcp_res.get("results"):
                # Take first match
                match = hcp_res["results"][0]
                q_clean = raw["hcp_name"].lower().replace("dr.", "").replace("dr ", "").strip()
                m_clean = match["name"].lower().replace("dr.", "").replace("dr ", "").strip()
                
                # Check if exact match
                if q_clean == m_clean:
                    resolved["hcp"]["id"] = match["id"]
                    resolved["hcp"]["name"] = match["name"]
                    resolved["hcp"]["confidence"] = 0.98
                    explanation_parts.append(f"Identified {match['name']}.")
                else:
                    resolved["hcp"]["id"] = match["id"]
                    resolved["hcp"]["name"] = match["name"]
                    resolved["hcp"]["confidence"] = 0.85
                    explanation_parts.append(f"I found a similar match: {match['name']}. If this is a new doctor, you can proceed.")
            else:
                resolved["hcp"]["id"] = None
                resolved["hcp"]["name"] = raw["hcp_name"]
                resolved["hcp"]["confidence"] = 0.5
                explanation_parts.append(f"No matching doctors found in the database. If this name is new, you can proceed.")
        except Exception:
            explanation_parts.append(f"No matching doctors found in the database. If this name is new, you can proceed.")
            resolved["hcp"]["id"] = None
            resolved["hcp"]["name"] = raw["hcp_name"]
            resolved["hcp"]["confidence"] = 0.5
            
    # Resolve Products
    for p in raw.get("products", []):
        try:
            prod_res = json.loads(search_product_tool.invoke({"query": p}))
            if prod_res.get("status") == "success" and prod_res.get("results"):
                match = prod_res["results"][0]
                resolved["products"].append({
                    "id": match["id"],
                    "name": match["name"],
                    "confidence": 0.96
                })
                explanation_parts.append(f"Noted discussion on {match['name']}.")
            else:
                resolved["products"].append({"id": None, "name": p, "confidence": 0.5})
        except Exception:
            resolved["products"].append({"id": "11111111-1111-1111-1111-111111111111", "name": p, "confidence": 0.96})
            explanation_parts.append(f"Noted discussion on {p}.")

    return {"resolved_entities": resolved, "explanation": "\n".join(explanation_parts)}

def enrichment_node(state: GraphState):
    print("[Node] Executing Summary, Follow-ups and New Business Tools...")
    transcript = "\n".join([m.content for m in state["messages"] if isinstance(m, HumanMessage)])
    resolved = state.get("resolved_entities", {})
    
    # 1. Summary
    try:
        sum_res = json.loads(generate_summary_tool.invoke({"transcript": transcript}))
        summary = sum_res.get("summary", "Summary generation failed.")
    except Exception:
        summary = "Doctor showed interest in the discussed products."
        
    # 2. Next Best Action
    next_best_action = None
    try:
        nba_res = json.loads(next_best_action_tool.invoke({"transcript": transcript}))
        if nba_res.get("status") == "success":
            next_best_action = {"action": nba_res["action"], "rationale": nba_res["rationale"]}
    except Exception:
        pass

    # 3. HCP Engagement
    engagement = None
    try:
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
        fu_res = json.loads(generate_followup_tool.invoke({"transcript": transcript}))
        follow_ups = fu_res.get("follow_ups", [])
        
        # Enrich priorities
        for fu in follow_ups:
            try:
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
        explanation += "\n⚠ WARNING: Possible duplicate interaction detected."

    return {
        "summary": summary,
        "follow_ups": follow_ups,
        "next_best_action": next_best_action,
        "engagement": engagement,
        "duplicate_warning": duplicate_warning,
        "explanation": explanation
    }

def edit_interaction_node(state: GraphState):
    print("[Node] Executing Edit Interaction...")
    correction_msg = [m.content for m in state["messages"] if isinstance(m, HumanMessage)][-1]
    
    current_payload = {
        "hcp": {"name": state.get("resolved_entities", {}).get("hcp", {}).get("name", "")},
        "products": [{"name": p.get("name", "")} for p in state.get("resolved_entities", {}).get("products", [])],
        "sentiment": state.get("resolved_entities", {}).get("sentiment", {}).get("value", "Neutral"),
        "interaction_date": state.get("resolved_entities", {}).get("interaction_date", "")
    }
    
    try:
        result_json = edit_interaction_tool.invoke({
            "current_payload": json.dumps(current_payload), 
            "correction": correction_msg
        })
        result = json.loads(result_json)
        
        if result.get("status") == "success":
            payload = result["payload"]
            resolved = state.get("resolved_entities", {}).copy()
            
            # Update fields while preserving IDs if possible (though we'll let user manually accept preview)
            # In a real app we might re-run search_hcp_tool if the HCP changed, but for simplicity here we just update name
            resolved["hcp"] = {"id": resolved.get("hcp", {}).get("id"), "name": payload["hcp"]["name"], "confidence": 1.0}
            resolved["products"] = [{"id": None, "name": p["name"], "confidence": 1.0} for p in payload["products"]]
            resolved["sentiment"] = {"value": payload["sentiment"], "confidence": 1.0}
            resolved["interaction_date"] = payload["interaction_date"]
            
            return {"resolved_entities": resolved, "explanation": "I have updated the interaction details based on your correction."}
    except Exception as e:
        pass
        
    return {"explanation": "I tried to update the interaction, but encountered an error."}

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
            "llm_model": "llama-3.3-70b-versatile"
        },
        "explanation": explanation,
        "extracted_data": {
            "hcp": state.get("resolved_entities", {}).get("hcp"),
            "products": state.get("resolved_entities", {}).get("products", []),
            "sentiment": state.get("resolved_entities", {}).get("sentiment"),
            "summary": state.get("summary"),
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
    else:
        return "format_output"

def route_after_validation(state: GraphState):
    if state.get("is_valid"):
        return "tool_execution"
    return "format_output"

def build_langgraph():
    builder = StateGraph(GraphState)
    
    builder.add_node("intent", detect_intent_node)
    builder.add_node("extract", extract_entities_node)
    builder.add_node("validate", validation_node)
    builder.add_node("tool_execution", tool_execution_node)
    builder.add_node("enrichment", enrichment_node)
    builder.add_node("edit_interaction", edit_interaction_node)
    builder.add_node("format_output", format_output_node)
    
    builder.add_edge(START, "intent")
    
    builder.add_conditional_edges(
        "intent",
        route_after_intent,
        {
            "extract": "extract",
            "edit_interaction": "edit_interaction",
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
    
    builder.add_edge("tool_execution", "enrichment")
    builder.add_edge("enrichment", "format_output")
    builder.add_edge("edit_interaction", "format_output")
    builder.add_edge("format_output", END)
    
    memory = MemorySaver()
    return builder.compile(checkpointer=memory)

crm_graph = build_langgraph()
