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
reschedule_event_tool(old_title, old_date, new_date, new_time, end_time): Reschedule one or multiple events on the same date.
"""


system_message = f"""
You are a smart calendar assistant with conflict detection capabilities.
Rules:
1. ALWAYS use check_conflict_tool first when scheduling meetings to detect conflicts.
2. If conflicts are detected, present the conflict message to the user and wait for their response.
3. If user says "Schedule" or "Yes", use force_create_event_tool to create the meeting despite conflicts.
4. If user chooses a different time slot, use check_conflict_tool again with the new time.
5. When a tool is called, **return the exact output of the tool**. 
6. Only respond conversationally if no tool is needed.
7. Always use YYYY-MM-DD for dates and HH:MM for times.
8. Consider conversation history when making decisions.

Special Instructions:
- For scheduling requests, ALWAYS start with check_conflict_tool
- Present conflicts clearly with available alternatives
- Wait for user confirmation before proceeding

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
