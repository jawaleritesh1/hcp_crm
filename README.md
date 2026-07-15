# AI-First CRM HCP Module — Log Interaction Screen

An intelligent, AI-first Customer Relationship Management (CRM) module designed for life science field representatives to log, query, and edit healthcare professional (HCP) interactions using conversational natural language (text or voice) or a structured UI form.

---



## 🛠️ Technology Stack

| Layer | Technologies | Key Features |
|---|---|---|
| **Frontend** | React 18, TypeScript, Redux Toolkit, Material UI (MUI v5) | Redux state syncing, Inter typography, pulsing record animations |
| **Voice Note** | HTML5 Web Speech API (`webkitSpeechRecognition`) | Real-time speech-to-text directly in the chat panel |
| **Backend** | Python 3.10+, FastAPI, SQLAlchemy, PostgreSQL / SQLite | High-throughput async REST endpoints, auto-seeding |
| **AI Orchestration** | LangGraph, Groq API (`llama-3.3-70b-versatile`) | Intent-routing state machine, persistent thread session memory |

---

## 🧠 LangGraph Agent Architecture

The AI assistant runs a stateful, multi-turn LangGraph agent that analyzes raw text/voice inputs and routes them through a structured pipeline:

```
                      ┌──────────────────┐
                      │  User Chat /     │
                      │  Spoken Voice    │
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
     │  Engagement,  │ │  Engagement,  │
     │  Priority,    │ │  Priority,    │
     │  Duplicate Chk│ │  Duplicate Chk│
     └───────┬───────┘ └───────┬───────┘
             ▼                 ▼
     ┌───────────────┴─────────────────┐
     │      Format Output Node         │
     └─────────────────────────────────┘
```

### Specialized AI Tools (12)
1. **`log_interaction_tool`** *(Mandatory)*: Extracts HCP details, products discussed, date, sentiment, and outcomes.
2. **`edit_interaction_tool`** *(Mandatory)*: Corrects form details in-place using natural language instructions.
3. **`search_hcp_tool`**: Fuzzy database match for HCP name resolution.
4. **`search_product_tool`**: Resolves brand drug names (e.g. "CardioPlus") to system product UUIDs.
5. **`generate_summary_tool`**: Compiles interactions into standardized medical meeting summaries.
6. **`generate_followup_tool`**: Automatically extracts actions and flags deadline targets.
7. **`next_best_action_tool`**: Suggests next steps with business rationales.
8. **`hcp_engagement_tool`**: Evaluates rep interest, engagement scores, and prescription readiness.
9. **`duplicate_interaction_tool`**: Safeguards against double-logging by warning users about duplicate entries.
10. **`priority_recommendation_tool`**: Analyzes tasks to set priority status (High/Medium/Low) based on severity.
11. **`search_interaction_history_tool`**: Fetches interaction logs for a target doctor sorted newest first.
12. **`manage_followups_tool`**: Complete follow-ups or query them by date ranges (*today, this week, overdue, all*).

---

## 🚀 The 5 Core Interactive AI Flows

### 1. Log a New Interaction (Entity Extraction & Auto-population)
* **Action:** Speak or type: `"I met Dr. Sharma today. We discussed CardioPlus. The sentiment was positive and he requested samples by next Monday."`
* **Result:** Form automatically populates. If names are ambiguous (e.g. multiple "Sharma"s), the AI displays interactive select buttons in the chat bubble.

### 2. Live Form Correction (Conversational Editing)
* **Action:** Type: `"Actually, change HCP to Dr. Rohan Mehta and set the date to yesterday."`
* **Result:** Form updates instantly. Old HCP name (`Dr. Ananya Kulkarni`) is programmatically stripped from attendees, summaries, and follow-ups and replaced with the new HCP name.

### 3. Search for HCPs (CRM Doctor Lookup)
* **Action:** Type: `"Find Dr. Nair in the system."`
* **Result:** The agent queries database profiles and returns quick-select button cards (`Dr. Priya Nair`, `Dr. Priyanka Nair`).

### 4. View Interaction History (CRM Timeline Retrieval)
* **Action:** Click a doctor's card or type: `"Show my past meetings with Dr. Priya Nair."`
* **Result:** Retreives past logs, displaying them in a chronological history timeline.

### 5. Follow-ups Management Checklist
* **Action:** Type: `"What follow-up tasks are due this week?"` or `"Mark the task 'Send the latest clinical study' as completed."`
* **Result:** The agent applies time-filters (*today, this week, overdue, all*) or updates task records in the DB, syncing the checklist UI instantly.

---

## 💻 Installation & Setup

### Backend Setup
```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate a python virtual environment
python -m venv venv
source venv/Scripts/activate  # On Windows: venv\Scripts\activate

# 3. Install required packages
pip install -r requirements.txt

# 4. Create a .env file with configuration
# DATABASE_URL=postgresql://username:password@localhost:5432/hcp_crm
# GROQ_API_KEY=your_groq_api_key

# 5. Run database migrations
alembic upgrade head

# 6. Seed mock database entries (creates initial HCPs, products, and history)
python scripts/seed.py

# 7. Start FastAPI application server
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev

# 4. Launch http://localhost:5173/ in your browser
```

---

## 🔒 Proxy Configuration & CORS
Frontend requests are handled via a local dev server proxy configured in `vite.config.ts` mapping `/api` requests to backend port `8000`. This completely removes CORS blocks and ensures robust same-machine networking.
