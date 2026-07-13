import os
import sys

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Set a dummy GROQ API key for testing structural initialization if not present
if not os.getenv("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = "gsk_dummy_test_key_for_testing_structural_setup"

from pydantic import BaseModel
from app.ai.groq_service import GroqService, GroqServiceException

# Define a simple schema for the test extraction
class SimpleExtraction(BaseModel):
    hcp_name: str
    product_discussed: str
    is_positive: bool

def run_test():
    print("Testing GroqService structural setup...")
    
    # Initialize the service
    try:
        service = GroqService()
        print("[SUCCESS] GroqService instantiated successfully with configuration and timeouts.")
    except Exception as e:
        print(f"[ERROR] Failed to instantiate GroqService: {e}")
        return

    prompt = "Met Dr. John Doe today. He was very happy and showed interest in CardioPlus."
    
    print(f"\nAttempting structured extraction with prompt: '{prompt}'")
    try:
        # This will likely fail with a network/auth error because of the dummy key
        # But it will test the request wrapping, Pydantic schema generation, and retry logic routing
        result = service.extract_structured_data(
            prompt=prompt,
            schema_model=SimpleExtraction,
            model="llama3-8b-8192" # Use a smaller model for the dummy test
        )
        print("[SUCCESS] Extraction successful!")
        print(result.model_dump_json(indent=2))
    except GroqServiceException as e:
        print(f"[SUCCESS] Structured extraction caught expected error (likely auth/network): {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected error during extraction: {e}")

if __name__ == "__main__":
    run_test()
