import os
import sys
import json
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from app.core.database import SessionLocal
from app.models.models import HCP, Interaction, Product
from app.ai.graph_service import graph_service

def clean_database():
    db = SessionLocal()
    try:
        # Delete test interactions
        db.query(Interaction).filter(Interaction.topics_discussed.like("%[QA TEST]%")).delete(synchronize_session=False)
        # Delete test HCPs
        db.query(HCP).filter(HCP.email.like("%qa_test%")).delete(synchronize_session=False)
        db.commit()
    except Exception as e:
        print("Clean database error:", e)
        db.rollback()
    finally:
        db.close()

def seed_qa_data():
    clean_database()
    db = SessionLocal()
    try:
        # Seed an ambiguous Rajesh Sharma
        hcp_ambig = HCP(
            first_name="Rajesh",
            last_name="Sharma",
            specialty="Pediatrics",
            email="qa_test_rajesh@example.com"
        )
        db.add(hcp_ambig)
        db.commit()
        db.refresh(hcp_ambig)
        
        # Get existing Rajiv Sharma
        hcp_rajiv = db.query(HCP).filter(HCP.last_name == "Sharma", HCP.first_name == "Rajiv").first()
        if not hcp_rajiv:
            hcp_rajiv = HCP(
                first_name="Rajiv",
                last_name="Sharma",
                specialty="Cardiology",
                email="qa_test_rajiv@example.com"
            )
            db.add(hcp_rajiv)
            db.commit()
            db.refresh(hcp_rajiv)
            
        # Get product
        product = db.query(Product).filter(Product.name == "CardioPlus").first()
        if not product:
            product = Product(name="CardioPlus", therapeutic_area="Cardiovascular")
            db.add(product)
            db.commit()
            db.refresh(product)
            
        # Seed existing interaction for duplicate test
        db_interaction = Interaction(
            hcp_id=hcp_rajiv.id,
            interaction_date=datetime.utcnow(),
            sentiment="Positive",
            topics_discussed="[QA TEST] Discussed CardioPlus with Dr. Rajiv Sharma"
        )
        db.add(db_interaction)
        db.commit()
        
        return hcp_rajiv.id, hcp_ambig.id
    except Exception as e:
        print("Seeding QA data failed:", e)
        db.rollback()
    finally:
        db.close()

def test_scenarios():
    print("====================================================")
    print("STARTING E2E QA VALIDATION FOR LANGGRAPH WORKFLOW")
    print("====================================================")
    
    rajiv_id, ambig_id = seed_qa_data()
    thread_id = "qa-validation-thread-999"
    
    try:
        # Scenario A: New Interaction (Positive, CardioPlus, Clinical Evidence)
        print("\n--- Scenario A: New Interaction ---")
        prompt_a = "Met with Dr. Rajiv Sharma today. Discussed CardioPlus. The doctor showed great interest, positive sentiment. Please send him clinical evidence by next week."
        print(f"Input: {prompt_a}")
        res_a = graph_service.process_message(prompt_a, thread_id)
        
        trace_a = res_a["meta"]["execution_trace"]
        ext_a = res_a["extracted_data"]
        
        print(f"Trace: {trace_a}")
        print(f"HCP ID: {ext_a['hcp']['id']}")
        print(f"HCP Name: {ext_a['hcp']['name']}")
        print(f"HCP Confidence: {ext_a['hcp']['confidence']}")
        print(f"Engagement Score: {ext_a['engagement']['score']}")
        print(f"Follow-ups: {ext_a['follow_ups']}")
        print(f"NBA Action: {ext_a['next_best_action']['action']}")
        print(f"Duplicate Warning: {ext_a['duplicate_warning']}")
        
        assert ext_a["hcp"]["id"] == str(rajiv_id)
        assert len(ext_a["materials_shared"]) == 1
        assert ext_a["materials_shared"][0]["name"] == "CardioPlus"
        assert ext_a["engagement"]["score"] > 70
        assert ext_a["follow_ups"][0]["priority"] == "High"  # clinical evidence should be High
        assert "priority_recommendation_tool" in trace_a
        
        # Scenario B: Edit Interaction (Anita Desai, preserve products/sentiment, regenerate summary)
        print("\n--- Scenario B: Edit Interaction ---")
        prompt_b = "Actually, the doctor was Anita Desai."
        print(f"Input: {prompt_b}")
        res_b = graph_service.process_message(prompt_b, thread_id)
        
        trace_b = res_b["meta"]["execution_trace"]
        ext_b = res_b["extracted_data"]
        
        print(f"Trace: {trace_b}")
        print(f"HCP Name: {ext_b['hcp']['name']}")
        print(f"HCP ID: {ext_b['hcp']['id']}")
        print(f"Preserved Products: {[p['name'] for p in ext_b['materials_shared']]}")
        
        assert "Anita Desai" in ext_b["hcp"]["name"]
        assert ext_b["hcp"]["id"] != str(rajiv_id) # must resolve to Anita Desai's ID
        assert len(ext_b["materials_shared"]) == 1 # products must be preserved
        assert ext_b["materials_shared"][0]["name"] == "CardioPlus"
        assert "edit_interaction_tool" in trace_b
        
        # Scenario C: Multiple Products
        print("\n--- Scenario C: Multiple Products ---")
        thread_id_c = "qa-validation-thread-c"
        prompt_c = "Had a chat with Dr. Anita Desai. Discussed CardioPlus and NeuroMax. Objections raised about pricing, neutral mood."
        print(f"Input: {prompt_c}")
        res_c = graph_service.process_message(prompt_c, thread_id_c)
        ext_c = res_c["extracted_data"]
        print(f"Products Resolved: {[p['name'] for p in ext_c['materials_shared']]}")
        print(f"Engagement Score: {ext_c['engagement']['score']}")
        
        assert len(ext_c["materials_shared"]) == 2
        assert ext_c["engagement"]["score"] < ext_a["engagement"]["score"]  # neutral + objections should lower engagement
        
        # Scenario D: Ambiguous HCP Lookup
        print("\n--- Scenario D: Ambiguous HCP Lookup ---")
        thread_id_d = "qa-validation-thread-d"
        prompt_d = "Met Dr. Sharma today. Discussed CardioPlus."
        print(f"Input: {prompt_d}")
        res_d = graph_service.process_message(prompt_d, thread_id_d)
        ext_d = res_d["extracted_data"]
        print(f"HCP ID: {ext_d['hcp']['id']}")
        print(f"HCP Confidence: {ext_d['hcp']['confidence']}")
        print(f"Explanation: {res_d['explanation']}")
        
        assert ext_d["hcp"]["id"] is None
        assert ext_d["hcp"]["confidence"] == 0.60
        assert "multiple matching doctors" in res_d["explanation"].lower()
        
        # Scenario E: Duplicate Interaction
        time.sleep(3)
        print("\n--- Scenario E: Duplicate Interaction Warning ---")
        thread_id_e = "qa-validation-thread-e"
        prompt_e = "Met Dr. Rajiv Sharma today. Discussed CardioPlus. Same meeting we logged earlier."
        print(f"Input: {prompt_e}")
        res_e = graph_service.process_message(prompt_e, thread_id_e)
        ext_e = res_e["extracted_data"]
        print(f"Duplicate Found: {ext_e['duplicate_warning']['duplicate_found']}")
        # Print encoding-safe explanation
        print(f"Warning: {res_e['explanation'].encode('ascii', errors='replace').decode('ascii')}")
        
        assert ext_e["duplicate_warning"]["duplicate_found"] is True
        
        # Scenario F: Negative Interaction
        time.sleep(3)
        print("\n--- Scenario F: Negative Interaction ---")
        thread_id_f = "qa-validation-thread-f"
        prompt_f = "Met Dr. Rajiv Sharma. Negative discussion, doctor expressed severe objections to CardioPlus and refused to proceed. Objections raised, obdurate stance."
        print(f"Input: {prompt_f}")
        res_f = graph_service.process_message(prompt_f, thread_id_f)
        ext_f = res_f["extracted_data"]
        print(f"Engagement Score: {ext_f['engagement']['score']}")
        
        assert ext_f["engagement"]["score"] < 50
        
        # Scenario G: Low Priority Follow-up
        time.sleep(3)
        print("\n--- Scenario G: Low Priority Follow-up ---")
        thread_id_g = "qa-validation-thread-g"
        prompt_g = "Met Dr. Rajiv Sharma. Routine catchup. Logged meeting, no follow-up requested by the doctor."
        print(f"Input: {prompt_g}")
        res_g = graph_service.process_message(prompt_g, thread_id_g)
        ext_g = res_g["extracted_data"]
        print(f"Follow-ups: {ext_g['follow_ups']}")
        
        if ext_g["follow_ups"]:
            print(f"Follow-up Priority: {ext_g['follow_ups'][0]['priority']}")
            assert ext_g["follow_ups"][0]["priority"] in ["Medium", "Low"]
            
        print("\n====================================================")
        print("ALL E2E SCENARIOS VALIDATED SUCCESSFULLY!")
        print("====================================================")
        
    finally:
        clean_database()

if __name__ == "__main__":
    test_scenarios()
