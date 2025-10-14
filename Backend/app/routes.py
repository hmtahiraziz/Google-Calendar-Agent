from fastapi import APIRouter
from app.models.request_model import QueryRequest, Message
from app.tools.agent import create_calendar_agent
from app.tools.calendar_tools import parse_date

router = APIRouter()
agent = create_calendar_agent()  

tool_descriptions = """
check_conflict_tool(title, date, time): Check for scheduling conflicts before creating an event. Use this first when scheduling meetings.
force_create_event_tool(title, date, time): Force create an event even if there are conflicts. Use when user confirms "Schedule".
create_event_tool(title, date, time): Create a calendar event. Supports natural language time ranges ("10am to 12pm", "at 3pm for 2 hours").
list_events_tool(date): List all events on a given date (YYYY-MM-DD).
find_free_slots_tool(date): Show free time slots.
cancel_event_tool(title, date): Cancel one or multiple events by title or all events on a date.
reschedule_with_conflict_check_tool(old_title, old_date, new_date, new_time, end_time): **PRIMARY RESCHEDULE TOOL** - Reschedule events with conflict detection and available slot suggestions. Use "all" as old_title to reschedule all meetings on a date. ALWAYS use this for rescheduling requests.
force_reschedule_tool(old_title, old_date, new_date, new_time, end_time): Force reschedule events despite conflicts. Use when user confirms "Force reschedule".
reschedule_event_tool(old_title, old_date, new_date, new_time, end_time): **LEGACY TOOL** - Do not use this. Use reschedule_with_conflict_check_tool instead.
schedule_multiple_meetings_tool(query): Schedule multiple meetings from a single request with conflict detection. Use when user requests multiple meetings with "and".
cancel_multiple_meetings_tool(query): Cancel multiple specific meetings from a single request. Use when user requests multiple cancellations with "and".
"""


system_message = f"""
You are a smart calendar assistant with conflict detection capabilities.
Rules:
1. ALWAYS use check_conflict_tool first when scheduling meetings to detect conflicts.
2. **CRITICAL: ALWAYS use reschedule_with_conflict_check_tool for ALL rescheduling requests. NEVER use reschedule_event_tool.**
3. For multiple meetings in one request (with "and" or commas), use schedule_multiple_meetings_tool.
4. For multiple cancellations in one request (with "and" or commas), use cancel_multiple_meetings_tool.
5. If conflicts are detected, present the conflict message to the user and wait for their response.
6. If user says "Schedule" or "Yes", use force_create_event_tool to create the meeting despite conflicts.
7. If user says "Force reschedule", use force_reschedule_tool to reschedule despite conflicts.
8. If user chooses a different time slot, use the appropriate tool again with the new time.
9. When a tool is called, **return the exact output of the tool**. 
10. Only respond conversationally if no tool is needed.
11. Always use YYYY-MM-DD for dates and HH:MM for times.
12. **IMPORTANT: Always consider conversation history when making decisions.**
13. **If user provides a time slot like "09:00-12:00" after a conflict was shown, use that time slot with the original meeting details.**

**CRITICAL RESCHEDULING PATTERNS:**
- **"Reschedule All meetings on [date] to [new_date]"** = Use reschedule_with_conflict_check_tool("all", old_date, new_date, "same time")
- **"Reschedule all my meetings on [date] to [new_date]"** = Use reschedule_with_conflict_check_tool("all", old_date, new_date, "same time")
- **"Move all meetings from [date] to [new_date]"** = Use reschedule_with_conflict_check_tool("all", old_date, new_date, "same time")
- **"Reschedule everything on [date] to [new_date]"** = Use reschedule_with_conflict_check_tool("all", old_date, new_date, "same time")
- **"All meetings"** in reschedule context = Use "all" as the old_title parameter
- **DO NOT ask for clarification when user says "All meetings" - immediately use the reschedule tool**

Multi-Meeting Support:
- **Scheduling**: Detect multiple meetings using keywords: "and", commas, multiple "schedule" commands
- **Cancellation**: Detect multiple cancellations using keywords: "and", commas, multiple "delete/cancel" commands
- Parse each meeting individually with enhanced parsing
- Check conflicts for all meetings (scheduling only)
- Present conflicts with available alternatives
- Allow partial operations (some succeed, others have conflicts)

Special Instructions:
- For single meeting requests, use check_conflict_tool
- For multiple meeting requests, use schedule_multiple_meetings_tool
- For single cancellations, use cancel_event_tool
- For multiple cancellations, use cancel_multiple_meetings_tool
- **CRITICAL: For ALL rescheduling requests, ALWAYS use reschedule_with_conflict_check_tool (NOT reschedule_event_tool)**
- **CRITICAL: When user says "All meetings" or "all my meetings", immediately use reschedule_with_conflict_check_tool with "all" as old_title**
- Present conflicts clearly with available alternatives
- Wait for user confirmation before proceeding
- **When user selects a time slot from available options, use the original meeting title and date with the new time**

Tools available:
{tool_descriptions}
"""

@router.get("/")
def root():
    return {"message": "🚀 Calendar Agent is running"}


@router.post("/ask")
def ask_agent(request: QueryRequest):
    user_query = request.query
    conversation_history = request.conversation_history or []

    resolved_date = parse_date(user_query)
    if resolved_date:
        user_query = user_query.lower()
        user_query = user_query.replace("today", resolved_date)
        user_query = user_query.replace("tomorrow", resolved_date)

        for day in ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]:
            user_query = user_query.replace(day, resolved_date)

    # Build messages with conversation history (last 5 messages)
    messages = [("system", system_message)]
    
    # Add conversation history (last 5 messages)
    for msg in conversation_history[-5:]:
        messages.append((msg.role, msg.content))
    
    # Add current user query
    messages.append(("user", user_query))

    response = agent.invoke({"messages": messages})
    content = response["messages"][-1].content

    return {"response": content}
