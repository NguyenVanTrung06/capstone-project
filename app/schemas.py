from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user message to send to the agent system.")
    session_id: Optional[str] = Field("default-session", description="Session identifier to persist chat history.")

class TelemetryEvent(BaseModel):
    agent_name: str
    action: str
    details: str
    timestamp: str

class ChatResponse(BaseModel):
    response: str = Field(..., description="The final agent response text.")
    telemetry: List[TelemetryEvent] = Field(default=[], description="The sequence of agent and tool executions during this turn.")

class TaskSchema(BaseModel):
    id: Optional[str] = None
    title: str
    priority: str = Field("Medium", pattern="^(Low|Medium|High)$")
    due_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: str = Field("Todo", pattern="^(Todo|In Progress|Done)$")

class CalendarEventSchema(BaseModel):
    id: Optional[str] = None
    title: str
    start_time: str
    end_time: str
    description: Optional[str] = ""
