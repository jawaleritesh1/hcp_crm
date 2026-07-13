# HCP Log Interaction CRM

AI-powered CRM module for capturing Healthcare Professional interactions.

## Project Structure
- `/backend`: FastAPI backend and AI logic
- `/frontend`: React + Vite frontend

## Setup Instructions
(TBD)

## AI Model Migration Note
**Important:** Originally designed for `gemma2-9b-it`, this system has been migrated to `llama-3.3-70b-versatile`. This migration was necessary because Groq officially decommissioned the Gemma 2 model. The system architecture seamlessly transitioned without altering core extraction schemas.

### LangGraph Architecture
The AI processing pipeline utilizes LangGraph to manage complex, multi-stage interaction processing. The workflow is divided into three distinct phases containing 10 enterprise AI tools.

#### Phase 1: Entity Extraction & Intent Routing
- **Detect Intent Node**: Determines the conversation intent (greeting, help, log_interaction, edit).
- **Log Interaction Tool (`log_interaction_tool`)**: Extracts initial entities (HCP Name, Products, Sentiment, Date) from the raw transcript.

#### Phase 2: Tool Execution (Entity Resolution)
- **Search HCP Tool (`search_hcp_tool`)**: Queries the CRM database to resolve a Healthcare Professional's exact UUID based on the extracted name.
- **Search Product Tool (`search_product_tool`)**: Queries the CRM database to resolve mentioned pharmaceutical products into exact UUIDs.

#### Phase 3: Enrichment & Decision Support
- **Generate Summary Tool (`generate_summary_tool`)**: Synthesizes the raw conversation transcript into a professional CRM interaction summary.
- **Generate Follow-up Tool (`generate_followup_tool`)**: Extracts promised or implied follow-up action items and calculates concrete due dates.
- **Next Best Action Tool (`next_best_action_tool`)**: Analyzes the interaction and recommends the next best sales action with a business rationale.
- **HCP Engagement Analysis Tool (`hcp_engagement_tool`)**: Calculates quantitative metrics including Engagement Score (0-100), Interest Level, and Prescription Readiness.
- **Duplicate Interaction Detection Tool (`duplicate_interaction_tool`)**: Scans existing logged interactions for the same HCP to detect possible duplicates and issues a warning.
- **Priority Recommendation Tool (`priority_recommendation_tool`)**: AI decision support that determines the priority (Critical, High, Medium, Low) of follow-up actions and provides business reasoning.

#### Edit Workflow (Transformation)
- **Edit Interaction Tool (`edit_interaction_tool`)**: Applies natural language corrections to an existing interaction payload, outputting the fully updated structure while preserving context and IDs.
# hcp_crm
