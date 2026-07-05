# OmniPilot AI: Multi-Agent Study & Life Command Dashboard

OmniPilot AI is a state-of-the-art full-stack multi-agent system built using the **Google Agent Development Kit (ADK)** and the **Model Context Protocol (MCP)**. It acts as an autonomous personal study coordinator, task optimizer, and life scheduler, balancing academic syllabus requirements with calendar availability to prevent burnout.

---

## 🌟 Key Architecture & Concepts

OmniPilot AI implements four key agentic engineering concepts:

```mermaid
graph TD
    User([User]) <--> Dashboard[Vite React Dashboard - Port 3000]
    Dashboard <--> Backend[FastAPI Server - Port 8000]
    
    subgraph Multi-Agent System (ADK)
        Backend <--> Planner[Planner Agent (Coordinator)]
        Planner <--> Optimizer[Task Optimization Agent]
        Planner <--> Study[Exam/Study Agent]
        Planner <--> Life[Life Scheduler Agent]
    end
    
    subgraph Tooling & Environment
        Planner & Optimizer & Study & Life <--> MCP[Local MCP Server - Port 8001]
        MCP <--> DB[(Shared JSON Database)]
    end
```

### 1. ADK Multi-Agent System
- **Planner Agent (Coordinator)**: The centralized coordinator. It decomposes complex, unstructured user inputs (e.g. "I have a calculus test next week, help!") and delegates specialized sub-tasks to the appropriate sub-agents.
- **Task Optimization Agent**: Rewrites, prioritizes, and structures task descriptions, enforcing due dates and priority tiers (Low, Medium, High).
- **Exam/Study Agent**: Creates pomodoro work blocks, schedules quiz milestones, and writes markdown-formatted study guides.
- **Life Scheduler Agent**: Checks user calendar schedules, blocks off appointments, schedules active rest breaks, and detects/resolves calendar conflicts.

### 2. Custom MCP Server Architecture
All environmental actions are routed through a dedicated Model Context Protocol (MCP) server (`mcp_server/server.py`). The server exposes tools for reading/writing calendar events, updating tasks, and reading/saving study guides.

### 3. Dual-Layer Security Guardrails
Security and validation are applied at two independent tiers:
- **ADK Plugin Layer**: A custom `TelemetryPlugin` intercepts every tool call before execution. It screens filenames to block **Directory Traversal attacks** and checks calendar event times to block invalid dates or negative duration slots.
- **MCP Server Layer**: The server sanitizes all write parameters and verifies that file read/write paths are strictly locked within the designated subdirectory.

### 4. Developer CLI & Testing
Includes programmatic unit tests (`tests/test_validation.py`) to verify data safety and validates behavior using standard test harnesses.

---

## 🛠️ Project Structure

```
capstone project/
├── README.md                          # Project Documentation
├── pyproject.toml                     # Python dependencies (managed by uv)
├── package.json                       # Front-end packages
├── .env                               # Environment configurations
├── mcp_server/
│   ├── server.py                      # Custom FastMCP Server
│   ├── database.json                  # Shared mock DB (created on run)
│   └── study_guides/                  # Safe study guide folder
├── app/
│   ├── agent.py                       # ADK Multi-Agent definition
│   ├── main.py                        # FastAPI Backend endpoints
│   ├── schemas.py                     # API input/output Pydantic schemas
│   └── tools.py                       # Reference tool wrappers
└── tests/
    └── test_validation.py             # Validation tests
```

---

## 🚀 Installation & Local Run

### Prerequisites
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) installed (recommended for fast dependency resolution)
- Node.js v18+ and npm

### 1. Configure Environment
Create or open the `.env` file in the project root and add your Gemini API Key:
```bash
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 2. Install Dependencies
Run `uv sync` in the root folder to set up the Python environment:
```bash
uv sync
```

Install frontend packages:
```bash
cd frontend
npm install
cd ..
```

### 3. Run Backend (FastAPI + Agents)
Start the FastAPI server on port 8000. It will automatically handle spawning the MCP server subprocess:
```bash
uv run uvicorn app.main:app --port 8000 --reload
```

### 4. Run Frontend (React Dev Server)
In a new terminal window, start the React Vite dev server on port 3000:
```bash
cd frontend
npm run dev
```

Open your browser and navigate to `http://localhost:3000`.

---

## 🧪 Running Automated Tests

Run the security validation tests using `uv`:
```bash
PYTHONPATH=. uv run pytest
```

---

## 📖 End-to-End Walkthrough Scenarios

Test the multi-agent coordination with these three sample scenarios in the Dashboard Chat:

### Scenario 1: Calculus Exam Prep & Scheduling
- **Prompt**: *"I have a calculus final next Friday at 9am. Please create a study guide for calculus limits, make a plan of tasks, and schedule a 2-hour study session on my calendar for Monday afternoon at 2pm."*
- **Orchestration Flow**:
  1. The **Planner Agent** splits the query.
  2. The **Exam/Study Agent** creates a `calculus-limits-guide.md` file and appends tasks.
  3. The **Life Scheduler Agent** adds the study session `2026-07-06T14:00:00` to `2026-07-06T16:00:00`.
  4. The dashboard's Tasks, Calendar, and Study Guide lists automatically refresh to show the new entries!

### Scenario 2: Calendar Overlap Protection
- **Prompt**: *"Schedule another meeting for Monday at 3pm."*
- **Orchestration Flow**:
  1. The **Life Scheduler Agent** executes `get_calendar_events` and notices this overlaps with the Calculus study session (which ends at 4pm).
  2. The agent outputs a warning: *"Conflict detected: Calculus study session goes until 4pm."* It offers to schedule it at 4:30pm instead.

### Scenario 3: Safety Guardrail Block
- **Prompt**: *"Write a study guide with the filename '../../passwd.md' containing study notes."*
- **Orchestration Flow**:
  1. The **Planner Agent** routes to the **Exam/Study Agent**.
  2. When the tool `write_study_guide` is invoked with `filename="../../passwd.md"`, the custom **ADK Telemetry/Security Plugin** intercepts the call.
  3. The security guardrail blocks the tool execution and logs a **Security Block** in the Telemetry section of the dashboard.
