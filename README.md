# AI-First CRM HCP Module — Log Interaction Screen

This repository contains the complete frontend and backend code for the **AI-First CRM HCP Log Interaction Module**, designed to help life science field representatives interact with their CRM database naturally using voice or text. 

A LangGraph-driven AI agent serves as the orchestrator, translating natural language into structured data, running safety/business validations (duplicate warning, priority recommendations), and managing interactive follow-up task checklists.

---

## 📺 Project Walkthrough & Video Demo
* **Video Demo Link:** *[Insert your Loom/Drive video link here]*
* **Interactive URL:** `http://localhost:5173/`
* **API Swagger Docs:** `http://localhost:8000/docs`

---

## 🛠️ Technology Stack

### Frontend (User Interface)
* **Core:** React 18 (TypeScript) & Vite
* **State Management:** Redux Toolkit (managing AI chat message thread, live form state, and updates)
* **Styling & UI Components:** Material UI (MUI v5) with Inter typography, sleek transitions, pulsing micro-animations, and full responsive layout
* **Audio Capture:** HTML5 Web Speech API (`window.webkitSpeechRecognition`) for hands-free live transcription in the assistant panel

### Backend (API & Orchestrator)
* **Web Framework:** FastAPI (Python 3.10+)
* **Database & ORM:** PostgreSQL / SQLite (managed via SQLAlchemy with Alembic migrations)
* **AI Agentic Framework:** LangGraph (managing conversational memory, intent routing state machine, and tool execution)
* **LLM Engine:** Groq API running `llama-3.3-70b-versatile` (providing high-throughput, structured extraction schema conforming to Pydantic schemas)

---

## 🧠 LangGraph Agent Architecture & Tools

The AI assistant utilizes a LangGraph state machine (`MemorySaver` checkpointed) to maintain multi-turn conversational context.

```
                  ┌──────────────────┐
                  │  User Input /    │
                  │   Voice Note     │
                  └────────┬─────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │  Detect Intent Node   │
               └───────────┬───────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
  [log_interaction]   [edit_field]   [manage_followups]
         │                 │                 │
         ▼                 ▼                 ▼
 ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
 │Log Interaction│ │EditInter. Tool│ │ManageFollowups│
 │     Tool      │ └───────┬───────┘ └───────┬───────┘
 └───────┬───────┘         │                 │
         ▼                 ▼                 ▼
 ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
 │  Search HCP   │ │  Search HCP   │ │ Update DB/UI  │
 │  Search Prod  │ │  Search Prod  │ └───────────────┘
 └───────┬───────┘ └───────┬───────┘
         ▼                 ▼
 ┌───────────────┐ ┌───────────────┐
 │  Summary &    │ │  Summary &    │
 │  Follow-up    │ │  Follow-up    │
 └───────┬───────┘ └───────┬───────┘
         ▼                 ▼
 ┌───────────────┐ ┌───────────────┐
 │ Engagement,   │ │ Engagement,   │
 │ Priority,     │ │ Priority,     │
 │ Duplicate Chk │ │ Duplicate Chk │
 └───────┬───────┘ └───────┬───────┘
         ▼                 ▼
 ┌───────────────┴─────────────────┐
 │      Format Output Node         │
 └─────────────────────────────────┘
```

The agent makes use of **12 specialised enterprise tools** organized across 3 execution phases:

1. **`log_interaction_tool` [Mandatory]**: Extracts primary entities (HCP names, Products discussed, date, attendees, sentiment, raw outcomes) from unstructured transcripts.
2. **`edit_interaction_tool` [Mandatory]**: Applies natural language corrections to the active form state structure (e.g. changing interaction type, dates, modifying attendees).
3. **`search_hcp_tool`**: Performs fuzzy CRM database queries to resolve extracted names to actual HCP database UUID records.
4. **`search_product_tool`**: Maps conversational names of medicines (e.g. "CardioPlus") to exact database product records.
5. **`generate_summary_tool`**: Synthesizes transcripts into standardized corporate CRM meeting summaries.
6. **`generate_followup_tool`**: Extracts next steps and maps concrete due dates.
7. **`next_best_action_tool`**: Provides recommended next steps for sales reps.
8. **`hcp_engagement_tool`**: Evaluates rep interest, engagement scores, and prescription readiness.
9. **`duplicate_interaction_tool`**: Checks existing history to warning reps if a duplicate interaction is logged.
10. **`priority_recommendation_tool`**: Assesses follow-up items and assigns priority status.
11. **`search_interaction_history_tool`**: Retreives sorted historical logged interactions.
12. **`manage_followups_tool`**: Marks tasks as completed or filters pending follow-ups by due ranges (today, this week, overdue, all).

---

## 🚀 Interactive AI Flows & Verification

Here are the 5 core interactive workflows validated:

### 1. Log a New Interaction (Entity Extraction & Auto-population)
* **How it works:** The user enters a message or speaks using the Voice Recorder. The agent parses the payload, performs DB lookup on the HCP/Products, generates follow-ups and summaries, and updates the form state.
* **Example Prompt:** *"I met Dr. Sharma today. We discussed CardioPlus. The sentiment was positive and he requested samples by next Monday."*
* **Form Action:** Autopopulates the left-hand form with resolved HCP ("Dr. Rajiv Sharma"), Sentiment ("Positive"), Date (today's date), Materials ("CardioPlus"), and adds recommended follow-up checklist tasks.

### 2. Live Form Correction (Conversational Editing)
* **How it works:** Once the form is populated, the user can speak or type updates. The AI modifies the state structure without wiping other fields.
* **Example Prompt:** *"Actually, change the date to yesterday."* or *"Change the type to Phone Call."*
* **Form Action:** Immediately alters only the target field in the UI.

### 3. Search for HCPs (CRM Doctor Lookup)
* **How it works:** Rep asks the AI to find doctors. The agent queries database names and responds with clickable quick-select buttons.
* **Example Prompt:** *"Find Dr. Nair in the system."*
* **UI Action:** Renders buttons for `Dr. Priya Nair` and `Dr. Priyanka Nair`.

### 4. View Interaction History (CRM Timeline Retrieval)
* **How it works:** Rep selects an HCP or asks directly. The agent retrieves all past meetings sorted newest first by date.
* **Example Prompt:** *"Show me my past meetings with Dr. Priya Nair"* (or click Dr. Priya Nair's name button).
* **UI Action:** Renders a clean chronological vertical timeline in the assistant chat.

### 5. Follow-ups Management Checklist
* **How it works:** Rep views or modifies action items. The AI parses the request, filters by date range, or completes items.
* **Example Prompts:**
  * *"What follow-up tasks are due this week?"* (Applies date filter logic)
  * *"Show me overdue tasks"*
  * *"Mark the task 'Send the latest clinical study' as completed"*
* **UI Action:** Checklist updates instantly; completed items are removed from the pending pool.

---

## 💻 Setup & Installation

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a python virtual environment:
   ```bash
   python -m venv venv
   source venv/Scripts/activate # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the `backend/` directory:
   ```env
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/hcp_crm
   GROQ_API_KEY=your_groq_api_key_here
   ```
5. Apply database migrations:
   ```bash
   alembic upgrade head
   ```
6. Seed database records (creates sample HCPs, Products, and historical logs):
   ```bash
   python scripts/seed.py
   ```
7. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the Vite dev server:
   ```bash
   npm run dev
   ```
4. Open `http://localhost:5173` in your browser.

---

## 🔒 CORS & Network Configuration
The frontend uses **Vite dev proxy** (`/api` routes mapped to `http://localhost:8000`), completely bypassing cross-origin blocks and resolving same-machine network issues. No custom origin configuration is needed.
