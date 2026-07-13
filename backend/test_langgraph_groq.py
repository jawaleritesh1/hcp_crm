import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if not os.getenv("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = "gsk_dummy_key"

from app.ai.graph_service import graph_service

def run_tests():
    print("Testing LangGraph -> Groq Connection...\n")
    
    thread_id_1 = "conversation-1"
    
    print("--- CONVERSATION 1 ---")
    msg1 = "Met Dr. Sharma today. Discussed CardioPlus. Doctor showed interest. Needs samples next Monday."
    print(f"User: {msg1}")
    res1 = graph_service.process_message(msg1, thread_id_1)
    print("Graph Output:")
    print(json.dumps(res1, indent=2))
    
    print("\n--- CONVERSATION 2 (Correction in same thread) ---")
    msg2 = "Actually, the product was NeuroGuard."
    print(f"User: {msg2}")
    res2 = graph_service.process_message(msg2, thread_id_1)
    print("Graph Output:")
    print(json.dumps(res2, indent=2))
    
    print("\nTests complete.")

if __name__ == "__main__":
    run_tests()
