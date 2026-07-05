import os
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.genai import types
from google.adk.runners import InMemoryRunner

# Import agents and telemetry helpers
from app.agent import app as adk_app, get_telemetry, clear_telemetry
from app.schemas import ChatRequest, ChatResponse, TaskSchema, CalendarEventSchema

# Initialize FastAPI App
app = FastAPI(title="OmniPilot AI Backend", version="0.1.0")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the Vite origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths for the shared database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "../mcp_server/database.json")
STUDY_GUIDES_DIR = os.path.join(BASE_DIR, "../mcp_server/study_guides")

# Ensure directories exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(STUDY_GUIDES_DIR, exist_ok=True)

# Helper to load and save shared database
def get_db() -> dict:
    if not os.path.exists(DB_PATH):
        # Create standard schema if missing
        initial_db = {"tasks": [], "calendar": []}
        with open(DB_PATH, "w") as f:
            json.dump(initial_db, f, indent=4)
        return initial_db
    try:
        with open(DB_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {"tasks": [], "calendar": []}

def save_db(data: dict):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=4)

# Initialize the ADK InMemoryRunner
# InMemoryRunner handles sessions and triggers agent execution
runner = InMemoryRunner(app=adk_app)

# Session Init Schema
class SessionInitRequest(BaseModel):
    session_id: str = "omnipilot-dashboard"

# Session Initialization Endpoint
@app.post("/api/session/init")
async def session_init_endpoint(request: SessionInitRequest):
    session_id = request.session_id
    app_name = runner.app_name or "app"
    user_id = "user_1"
    
    try:
        session = await runner.session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
    except Exception:
        session = None
        
    if not session:
        # Initialize native ADK session state
        await runner.session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            state={}
        )
        
    # Ensure JSON DB structures are initialized
    db = get_db()
    if "tasks" not in db:
        db["tasks"] = []
    if "calendar" not in db:
        db["calendar"] = []
    save_db(db)
    
    return {"status": "initialized", "session_id": session_id}

# Chat Endpoint: Communicates with OmniPilot multi-agent system
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    # Clear telemetry logs for the new turn
    clear_telemetry()
    
    # Check if API keys are set
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="Gemini API Key is not set. Please set the GEMINI_API_KEY environment variable in a .env file."
        )

    try:
        # Check and initialize session before running
        app_name = runner.app_name or "app"
        user_id = "user_1"
        try:
            session = await runner.session_service.get_session(
                app_name=app_name,
                user_id=user_id,
                session_id=request.session_id
            )
        except Exception:
            session = None
            
        if not session:
            await runner.session_service.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=request.session_id,
                state={}
            )

        # Wrap the user text into a standard Gemini Content object
        new_message = types.Content(parts=[types.Part.from_text(text=request.message)])
        
        response_text = ""
        # Run agent in background, yielding events
        async for event in runner.run_async(
            user_id="user_1",
            session_id=request.session_id,
            new_message=new_message
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text
                        
        # Retrieve telemetry recorded during execution
        execution_telemetry = get_telemetry().copy()
        
        # If no response text was aggregated (e.g. error or empty)
        if not response_text:
            response_text = "I processed your request, but did not generate a text response. Please check the logs."
            
        return ChatResponse(
            response=response_text,
            telemetry=execution_telemetry
        )
        
    except Exception as e:
        # Capture error and return a detailed response
        error_event = {
            "agent_name": "System",
            "action": "Execution Error",
            "details": f"Error running agents: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        return ChatResponse(
            response=f"An error occurred while running the OmniPilot coordinator: {str(e)}",
            telemetry=get_telemetry() + [error_event]
        )

# Task Endpoints (Syncs Dashboard UI with Database)
@app.get("/api/tasks")
async def get_tasks():
    db = get_db()
    return db.get("tasks", [])

@app.post("/api/tasks")
async def add_task(task: TaskSchema):
    db = get_db()
    tasks = db.get("tasks", [])
    
    if task.id:
        # Update existing
        for t in tasks:
            if t.get("id") == task.id:
                t.update(task.model_dump())
                save_db(db)
                return {"message": "Task updated successfully", "task": t}
        raise HTTPException(status_code=404, detail="Task ID not found")
    else:
        # Create new
        new_id = str(max([int(t.get("id", 0)) for t in tasks] + [0]) + 1)
        new_task = task.model_dump()
        new_task["id"] = new_id
        tasks.append(new_task)
        db["tasks"] = tasks
        save_db(db)
        return {"message": "Task created successfully", "task": new_task}

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    db = get_db()
    tasks = db.get("tasks", [])
    updated_tasks = [t for t in tasks if t.get("id") != task_id]
    if len(tasks) == len(updated_tasks):
        raise HTTPException(status_code=404, detail="Task not found")
    db["tasks"] = updated_tasks
    save_db(db)
    return {"message": "Task deleted successfully"}

# Calendar Endpoints
@app.get("/api/calendar")
async def get_calendar():
    db = get_db()
    return db.get("calendar", [])

@app.post("/api/calendar")
async def add_calendar_event(event: CalendarEventSchema):
    db = get_db()
    calendar = db.get("calendar", [])
    
    # Backend-side validation
    try:
        s_dt = datetime.fromisoformat(event.start_time)
        e_dt = datetime.fromisoformat(event.end_time)
        if e_dt <= s_dt:
            raise HTTPException(status_code=400, detail="End time must be after start time")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
        
    if event.id:
        for c in calendar:
            if c.get("id") == event.id:
                c.update(event.model_dump())
                save_db(db)
                return {"message": "Event updated successfully", "event": c}
        raise HTTPException(status_code=404, detail="Event ID not found")
    else:
        new_id = str(max([int(c.get("id", 0)) for c in calendar] + [100]) + 1)
        new_event = event.model_dump()
        new_event["id"] = new_id
        calendar.append(new_event)
        db["calendar"] = calendar
        save_db(db)
        return {"message": "Event scheduled successfully", "event": new_event}

# Study Guide Endpoints
@app.get("/api/study-guides")
async def list_study_guides():
    try:
        files = [f for f in os.listdir(STUDY_GUIDES_DIR) if f.endswith(".md")]
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/study-guides/{filename}")
async def read_study_guide(filename: str):
    # Safety Check against directory traversal
    safe_name = os.path.basename(filename)
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename parameters.")
        
    target_path = os.path.join(STUDY_GUIDES_DIR, safe_name)
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Study guide not found")
        
    try:
        with open(target_path, "r") as f:
            return {"filename": safe_name, "content": f.read()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
