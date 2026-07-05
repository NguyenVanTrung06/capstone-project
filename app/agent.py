import os
from datetime import datetime
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# Load environment variables
load_dotenv()

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_SERVER_PATH = os.path.join(BASE_DIR, "../mcp_server/server.py")

# Ensure API key is set for standard Gemini API fallback
# (ADK automatically uses GenAI client which checks GEMINI_API_KEY or GOOGLE_API_KEY)
if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    # If not set, we'll write a warning, but let the client attempt auth via default gcp credentials
    print("Warning: Neither GEMINI_API_KEY nor GOOGLE_API_KEY environment variables are set. Ensure they are configured in a .env file or environment.")

# Global telemetry log to capture multi-agent steps
telemetry_log = []

def get_telemetry():
    """Access current telemetry logs."""
    return telemetry_log

def clear_telemetry():
    """Clear telemetry logs between chat turns."""
    telemetry_log.clear()

class TelemetryPlugin(BasePlugin):
    """Custom ADK Plugin for Security Checks & Multi-Agent Telemetry Logging."""
    
    async def before_agent_callback(self, *, callback_context=None, agent=None, **kwargs):
        agent_obj = agent or (callback_context.agent if callback_context and hasattr(callback_context, 'agent') else None)
        agent_name = agent_obj.name if agent_obj else "Unknown Agent"
        telemetry_log.append({
            "agent_name": agent_name,
            "action": "Agent Thinking",
            "details": f"Agent '{agent_name}' has been activated to process user query.",
            "timestamp": datetime.now().isoformat()
        })
        return None

    async def after_agent_callback(self, *, callback_context=None, agent=None, response_content=None, **kwargs):
        agent_obj = agent or (callback_context.agent if callback_context and hasattr(callback_context, 'agent') else None)
        agent_name = agent_obj.name if agent_obj else "Unknown Agent"
        telemetry_log.append({
            "agent_name": agent_name,
            "action": "Agent Completed",
            "details": f"Agent '{agent_name}' finished processing and returned response.",
            "timestamp": datetime.now().isoformat()
        })
        return None

    async def before_tool_callback(self, *, tool=None, tool_args=None, tool_context=None, **kwargs):
        if not tool:
            return None
        tool_name = tool.name
        tool_args = tool_args or {}
        
        # Dual-Layer Security: Guardrail 1 - Path Traversal check
        if tool_name == "write_study_guide" or tool_name == "read_study_guide":
            filename = tool_args.get("filename", "")
            if not filename or ".." in filename or "/" in filename or "\\" in filename:
                telemetry_log.append({
                    "agent_name": "Security Guardrail",
                    "action": "Execution Blocked",
                    "details": f"BLOCKED path traversal attempt in file tool: '{filename}'",
                    "timestamp": datetime.now().isoformat()
                })
                # Returning this dict bypasses actual tool execution and returns the error directly
                return {"status": "error", "message": "Security Error: Directory traversal blocked."}
        
        # Dual-Layer Security: Guardrail 2 - Calendar Date Range check
        if tool_name == "add_calendar_event":
            start_time = tool_args.get("start_time", "")
            end_time = tool_args.get("end_time", "")
            try:
                s_dt = datetime.fromisoformat(start_time)
                e_dt = datetime.fromisoformat(end_time)
                if e_dt <= s_dt:
                    telemetry_log.append({
                        "agent_name": "Security Guardrail",
                        "action": "Execution Blocked",
                        "details": f"BLOCKED invalid calendar range: End ({end_time}) <= Start ({start_time})",
                        "timestamp": datetime.now().isoformat()
                    })
                    return {"status": "error", "message": "Security Error: Calendar end time must be after start time."}
            except ValueError:
                return {"status": "error", "message": "Security Error: Invalid ISO datetime format."}
        
        # Standard Telemetry Log for safe tool execution
        args_str = ", ".join([f"{k}={v}" for k, v in tool_args.items()])
        telemetry_log.append({
            "agent_name": "System Tools",
            "action": "Tool Executing",
            "details": f"Executing tool '{tool_name}' with parameters ({args_str})",
            "timestamp": datetime.now().isoformat()
        })
        return None

    async def after_tool_callback(self, *, tool=None, tool_args=None, tool_context=None, result=None, **kwargs):
        if not tool:
            return None
        tool_name = tool.name
        resp_preview = str(result)
        if len(resp_preview) > 150:
            resp_preview = resp_preview[:147] + "..."
            
        telemetry_log.append({
            "agent_name": "System Tools",
            "action": "Tool Executed",
            "details": f"Tool '{tool_name}' finished. Result: {resp_preview}",
            "timestamp": datetime.now().isoformat()
        })
        return None

# Configure connection to our custom MCP server
mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="uv",
            args=["run", "python", MCP_SERVER_PATH]
        )
    )
)

# Define Model Name (using the stable gemini-2.5-flash to avoid 3.5 free tier quota limits)
MODEL_NAME = "gemini-2.5-flash"

# Define Specialized Agents
task_opt_agent = Agent(
    name="task_optimization_agent",
    model=MODEL_NAME,
    instruction="""You are the Task Optimization Agent.
Your job is to structure raw, messy task requests into clear, prioritized items.
CRITICAL: You MUST call 'add_or_update_task' to actually save/update the tasks in the database. Do NOT just output them as text.
Ensure each task has:
- Title (clear and concise)
- Priority (Low, Medium, or High)
- Due Date (YYYY-MM-DD)
- Status (Todo, In Progress, or Done)
Use 'get_tasks' to check the current task list first.
Always output the structured summary of tasks after calling the tool to save them.""",
    description="Specializes in parsing, organizing, and prioritizing task logs.",
    tools=[mcp_toolset]
)

study_agent = Agent(
    name="exam_study_agent",
    model=MODEL_NAME,
    instruction="""You are the Exam/Study Agent.
Your job is to design custom study schedules, create Pomodoro work intervals, and generate study guides.
CRITICAL: You MUST call 'write_study_guide' to save study guides to the database. Do NOT just print them.
When generating a study guide:
- Write it in markdown format.
- Ensure it contains clear sections: Objectives, Main Topics, and Review Questions.
- Save it with a descriptive, safe filename (e.g. 'linear-algebra-guide.md') by calling 'write_study_guide'.
Coordinate with the Task Optimization Agent if new study-related tasks need scheduling.""",
    description="Specializes in creating exam preparation plans, study intervals, and structured study guides.",
    tools=[mcp_toolset]
)

life_agent = Agent(
    name="life_scheduler_agent",
    model=MODEL_NAME,
    instruction="""You are the Life Scheduler Agent.
Your job is to manage the user's schedule, prevent burnout by scheduling breaks, and handle calendar appointments.
CRITICAL: You MUST call 'add_calendar_event' to schedule events. Do NOT just describe the event in text.
IMPORTANT:
- Always check the calendar for time overlaps using 'get_calendar_events' before booking.
- If there is a calendar conflict, notify the user or propose a non-conflicting time.
- Proactively schedule 15-minute breaks after intense study periods by calling 'add_calendar_event'.""",
    description="Specializes in schedule conflict resolution, calendar bookings, and work-life balance break scheduling.",
    tools=[mcp_toolset]
)

# Define Core Coordinator Agent
planner_agent = Agent(
    name="planner_agent",
    model=MODEL_NAME,
    instruction="""You are OmniPilot AI, the centralized coordinator agent.
Your mission is to assist users with study workflows, exam scheduling, task management, and lifestyle balance.
You coordinate three specialized sub-agents:
1. 'task_optimization_agent': use for structuring tasks, adjusting priorities, and listing task states.
2. 'exam_study_agent': use for study guide creation, study schedules, and mock quiz preparation.
3. 'life_scheduler_agent': use for managing calendar appointments, setting break times, and avoiding calendar overlap.

CRITICAL INSTRUCTIONS:
- You must NOT just describe the plan in text. You MUST call the appropriate tools (either directly or by transferring to sub-agents) to physically write the data to the system.
- If the user wants to add, reschedule, or check a calendar event, you or your 'life_scheduler_agent' MUST run 'add_calendar_event' or 'get_calendar_events'.
- If the user wants to add, complete, or check a task, you or your 'task_optimization_agent' MUST run 'add_or_update_task' or 'get_tasks'.
- If the user wants to create a study guide, you or your 'exam_study_agent' MUST run 'write_study_guide'.
- After calling the tools, the user's dashboard screen will automatically refresh in real-time. If you do not call the tools, the dashboard will remain empty!
- Decompose the user request and call the tools/transfer control sequentially as needed. Present a final consolidated, polished plan that ties their tasks, calendar events, and study materials together in a structured way.
Always keep a professional, encouraging tone.""",
    sub_agents=[task_opt_agent, study_agent, life_agent],
    tools=[mcp_toolset]
)

# Create the ADK App and register our Telemetry & Security Plugin
app = App(
    name="app",
    root_agent=planner_agent,
    plugins=[TelemetryPlugin(name="telemetry_plugin")]
)
