from typing import Dict, Any
from langchain_core.messages import HumanMessage
from app.ai.graph import crm_graph

class GraphExecutionService:
    """Service to handle execution and context management of the LangGraph workflow."""
    
    def process_message(self, message: str, thread_id: str) -> Dict[str, Any]:
        """
        Invokes the LangGraph workflow with a new message and a specific thread_id.
        The thread_id is used by the MemorySaver checkpointer to maintain conversation context.
        """
        config = {"configurable": {"thread_id": thread_id}}
        
        # Inject the human message into the graph
        initial_state = {
            "messages": [HumanMessage(content=message)]
        }
        
        # Execute graph (streams state updates until END)
        final_state = crm_graph.invoke(initial_state, config=config)
        
        # Return the structured JSON from the final node
        return final_state.get("final_output", {})

graph_service = GraphExecutionService()
