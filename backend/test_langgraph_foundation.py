import os
import sys

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.ai.graph_service import graph_service
from app.ai.graph import crm_graph

def run_test():
    print("Testing LangGraph Execution Foundation...\n")
    
    thread_id = "test-conversation-123"
    
    # Turn 1
    msg1 = "I met with Dr. Smith today and we talked about CardioPlus."
    print(f"User (Turn 1): {msg1}")
    result1 = graph_service.process_message(msg1, thread_id)
    
    print("\n[Result 1]")
    print(f"Intent: {result1['intent']}")
    print(f"Entities: {result1['extracted_entities']}")
    print(f"Is Valid: {result1['is_valid']}")
    print(f"AI Message: {result1['latest_ai_message']}")
    print(f"Messages in State: {result1['messages_count']}")
    
    print("\n" + "="*50 + "\n")
    
    # Turn 2: Same thread ID
    msg2 = "Actually, we also talked about NeuroGuard."
    print(f"User (Turn 2): {msg2}")
    result2 = graph_service.process_message(msg2, thread_id)
    
    print("\n[Result 2]")
    print(f"Intent: {result2['intent']}")
    print(f"Entities: {result2['extracted_entities']}")
    print(f"Is Valid: {result2['is_valid']}")
    print(f"AI Message: {result2['latest_ai_message']}")
    print(f"Messages in State: {result2['messages_count']}") # Should be > Turn 1 count due to MemorySaver
    
    if result2['messages_count'] > result1['messages_count']:
        print("\n[SUCCESS] MemorySaver checkpointer successfully maintained conversation context across turns!")
    else:
        print("\n[ERROR] Thread context was not maintained.")

if __name__ == "__main__":
    run_test()
