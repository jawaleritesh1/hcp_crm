import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

if not os.getenv("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = "gsk_dummy_key"

from app.ai.tools import (
    search_hcp_tool,
    search_product_tool,
    generate_summary_tool,
    generate_followup_tool,
    log_interaction_tool,
    edit_interaction_tool
)

def run_tests():
    print("Testing LangGraph Tools Independently...\n")

    # 1. Search HCP Tool
    try:
        print("1. Testing Search HCP Tool...")
        res = search_hcp_tool.invoke({"query": "Sharma"})
        print(f"   Result: {res}")
    except Exception as e:
        print(f"   [Error] {e}")

    # 2. Search Product Tool
    try:
        print("\n2. Testing Search Product Tool...")
        res = search_product_tool.invoke({"query": "CardioPlus"})
        print(f"   Result: {res}")
    except Exception as e:
        print(f"   [Error] {e}")

    # 3. Generate Summary Tool
    try:
        print("\n3. Testing Generate Summary Tool...")
        # With dummy key it will likely hit auth error, but tests the schema execution
        res = generate_summary_tool.invoke({"transcript": "Talked to Dr. Sharma about CardioPlus."})
        print(f"   Result: {res}")
    except Exception as e:
        print(f"   [Error] {e}")

    # 4. Generate Follow-up Tool
    try:
        print("\n4. Testing Generate Follow-up Tool...")
        res = generate_followup_tool.invoke({"transcript": "Doctor wants sample of CardioPlus by next Monday."})
        print(f"   Result: {res}")
    except Exception as e:
        print(f"   [Error] {e}")

    # 5. Log Interaction Tool
    try:
        print("\n5. Testing Log Interaction Tool...")
        res = log_interaction_tool.invoke({"transcript": "Met Dr. Smith, he loved NeuroGuard."})
        print(f"   Result: {res}")
    except Exception as e:
        print(f"   [Error] {e}")

    # 6. Edit Interaction Tool
    try:
        print("\n6. Testing Edit Interaction Tool...")
        current = json.dumps({"hcp_name": "Dr. Smith", "products": ["NeuroGuard"], "sentiment": "Positive"})
        res = edit_interaction_tool.invoke({"current_payload": current, "correction": "Actually it was Dr. Jones."})
        print(f"   Result: {res}")
    except Exception as e:
        print(f"   [Error] {e}")

    print("\nAll tools invoked. Validation complete.")

if __name__ == "__main__":
    run_tests()
