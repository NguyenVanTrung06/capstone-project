import os
import json
import re
from datetime import datetime
from typing import List, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# Initialize FastMCP Server
mcp = FastMCP("OmniPilot MCP Server")

# Paths and Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.json")
STUDY_GUIDES_DIR = os.path.join(BASE_DIR, "study_guides")

# Ensure study guides directory exists
os.makedirs(STUDY_GUIDES_DIR, exist_ok=True)

# Helper functions for Database
def load_db() -> dict:
    if not os.path.exists(DB_PATH):
        default_db = {
            "tasks": [
                {
                    "id": "1",
                    "title": "Complete Capstone Project Proposal",
                    "priority": "High",
                    "due_date": "2026-07-10",
                    "status": "In Progress"
                },
                {
                    "id": "2",
                    "title": "Review Multi-Agent Orchestration Patterns",
                    "priority": "Medium",
                    "due_date": "2026-07-08",
                    "status": "Todo"
                }
            ],
            "calendar": [
                {
                    "id": "101",
                    "title": "OmniPilot Team Sync",
                    "start_time": "2026-07-05T10:00:00",
                    "end_time": "2026-07-05T11:00:00",
                    "description": "Discussing ADK Multi-Agent architecture and MCP tools setup."
                }
            ]
        }
        with open(DB_PATH, "w") as f:
            json.dump(default_db, f, indent=4)
        return default_db
    
    try:
        with open(DB_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {"tasks": [], "calendar": []}

def save_db(db: dict):
    with open(DB_PATH, "w") as f:
        json.dump(db, f, indent=4)

# Sanitize Filename to prevent directory traversal
def sanitize_filename(filename: str) -> str:
    # Remove any directory traversal sequences
    name = os.path.basename(filename)
    # Allow only alphanumeric, hyphens, underscores, and single dot
    name = re.sub(r'[^a-zA-Z0-9_\-\.]', '', name)
    if not name.endswith(".md"):
        name += ".md"
    return name

# Tool: Get Tasks
@mcp.tool()
def get_tasks() -> str:
    """Retrieve the current list of prioritized tasks."""
    db = load_db()
    return json.dumps(db.get("tasks", []), indent=2)

# Tool: Add or Update Task (with input validation)
@mcp.tool()
def add_or_update_task(
    title: str, 
    priority: str, 
    due_date: str, 
    status: str, 
    task_id: Optional[str] = None
) -> str:
    """Add a new task or update an existing one.
    
    Args:
        title: Task description/title.
        priority: Must be 'Low', 'Medium', or 'High'.
        due_date: Target completion date in format 'YYYY-MM-DD'.
        status: Must be 'Todo', 'In Progress', or 'Done'.
        task_id: Optional ID for updating an existing task.
    """
    # Validation checks
    if priority not in ["Low", "Medium", "High"]:
        return "Error: Priority must be 'Low', 'Medium', or 'High'."
    
    if status not in ["Todo", "In Progress", "Done"]:
        return "Error: Status must be 'Todo', 'In Progress', or 'Done'."
    
    try:
        datetime.strptime(due_date, "%Y-%m-%d")
    except ValueError:
        return "Error: due_date must be in 'YYYY-MM-DD' format."
    
    db = load_db()
    tasks = db.get("tasks", [])
    
    if task_id:
        # Update existing
        for t in tasks:
            if t.get("id") == task_id:
                t["title"] = title
                t["priority"] = priority
                t["due_date"] = due_date
                t["status"] = status
                save_db(db)
                return f"Task '{title}' (ID: {task_id}) updated successfully."
        return f"Error: Task with ID {task_id} not found."
    else:
        # Create new
        new_id = str(max([int(t.get("id", 0)) for t in tasks] + [0]) + 1)
        new_task = {
            "id": new_id,
            "title": title,
            "priority": priority,
            "due_date": due_date,
            "status": status
        }
        tasks.append(new_task)
        db["tasks"] = tasks
        save_db(db)
        return f"Task '{title}' created successfully with ID: {new_id}."

# Tool: Get Calendar Events
@mcp.tool()
def get_calendar_events() -> str:
    """Retrieve all current calendar scheduling entries."""
    db = load_db()
    return json.dumps(db.get("calendar", []), indent=2)

# Tool: Add Calendar Event (with conflict detection and safety validation)
@mcp.tool()
def add_calendar_event(
    title: str, 
    start_time: str, 
    end_time: str, 
    description: str = ""
) -> str:
    """Schedule a new calendar event.
    
    Args:
        title: Event title.
        start_time: ISO format date-time string 'YYYY-MM-DDTHH:MM:SS'.
        end_time: ISO format date-time string 'YYYY-MM-DDTHH:MM:SS'.
        description: Brief description of the event.
    """
    # Validation checks
    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
    except ValueError:
        return "Error: Start and end times must be in ISO format 'YYYY-MM-DDTHH:MM:SS'."
    
    if end_dt <= start_dt:
        return "Error: End time must be strictly after start time."
        
    db = load_db()
    calendar = db.get("calendar", [])
    
    # Conflict Detection: check if any event overlaps
    overlaps = []
    for event in calendar:
        e_start = datetime.fromisoformat(event["start_time"])
        e_end = datetime.fromisoformat(event["end_time"])
        
        # Check overlap: (start1 < end2) and (end1 > start2)
        if start_dt < e_end and end_dt > e_start:
            overlaps.append(event)
            
    if overlaps:
        overlap_titles = ", ".join([f"'{o['title']}'" for o in overlaps])
        # Return conflict message (Life Scheduler agent will handle or prompt user)
        return f"Warning: Overlap detected with existing event(s): {overlap_titles}. Event not added."

    new_id = str(max([int(e.get("id", 0)) for e in calendar] + [100]) + 1)
    new_event = {
        "id": new_id,
        "title": title,
        "start_time": start_time,
        "end_time": end_time,
        "description": description
    }
    calendar.append(new_event)
    db["calendar"] = calendar
    save_db(db)
    return f"Calendar event '{title}' scheduled successfully from {start_time} to {end_time}."

# Tool: Write Study Guide (with path security traversal protection)
@mcp.tool()
def write_study_guide(filename: str, content: str) -> str:
    """Save a structured study guide file.
    
    Args:
        filename: Name of the file (e.g. 'calculus-guide.md').
        content: Markdown content of the study guide.
    """
    # Force sanitization of filename to prevent path traversal
    safe_name = sanitize_filename(filename)
    target_path = os.path.join(STUDY_GUIDES_DIR, safe_name)
    
    # Extra check: ensure path is strictly within STUDY_GUIDES_DIR
    real_path = os.path.realpath(target_path)
    real_dir = os.path.realpath(STUDY_GUIDES_DIR)
    
    if not real_path.startswith(real_dir):
        return "Security Violation: Attempted directory traversal detected. Write blocked."
        
    try:
        with open(target_path, "w") as f:
            f.write(content)
        return f"Study guide saved successfully at {safe_name}."
    except Exception as e:
        return f"Error writing study guide: {str(e)}"

# Tool: Read Study Guide
@mcp.tool()
def read_study_guide(filename: str) -> str:
    """Read contents of a saved study guide.
    
    Args:
        filename: Name of the file.
    """
    safe_name = sanitize_filename(filename)
    target_path = os.path.join(STUDY_GUIDES_DIR, safe_name)
    
    # Path safety check
    real_path = os.path.realpath(target_path)
    real_dir = os.path.realpath(STUDY_GUIDES_DIR)
    if not real_path.startswith(real_dir):
        return "Security Violation: Directory traversal detected."
        
    if not os.path.exists(target_path):
        return f"Error: Study guide '{safe_name}' not found."
        
    try:
        with open(target_path, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading study guide: {str(e)}"

# Tool: List Study Guides
@mcp.tool()
def list_study_guides() -> str:
    """List all saved study guides."""
    try:
        files = [f for f in os.listdir(STUDY_GUIDES_DIR) if f.endswith(".md")]
        return json.dumps(files, indent=2)
    except Exception as e:
        return f"Error listing study guides: {str(e)}"

if __name__ == "__main__":
    # Launch FastMCP (standard stdio when run without args)
    mcp.run()
