from fastapi import APIRouter
from app.models.request_model import QueryRequest
from app.tools.agent import create_calendar_agent
from app.tools.calendar_tools import parse_date

router = APIRouter()
agent = create_calendar_agent()  

tool_descriptions = """
create_event_tool(title, date, time): Create a calendar event. Supports natural language time ranges ("10am to 12pm", "at 3pm for 2 hours").
list_events_tool(date): List all events on a given date (YYYY-MM-DD).
find_free_slots_tool(date): Show free time slots.
cancel_event_tool(title, date): Cancel one or multiple events by title or all events on a date.
reschedule_event_tool(old_title, old_date, new_date, new_time, end_time): Reschedule one or multiple events on the same date.
"""


system_message = f"""
You are a smart calendar assistant. 
Rules:
1. Always use the provided tools (create, list, cancel, reschedule, find free slots).
2. When a tool is called, **return the exact output of the tool**. 
   Do NOT paraphrase or generate extra text.
3. Only respond conversationally if no tool is needed.
4. Always use YYYY-MM-DD for dates and HH:MM for times.

Special Instructions:

Tools available:
{tool_descriptions}
"""

@router.get("/")
def root():
    return {"message": "🚀 Calendar Agent is running"}


@router.post("/ask")
def ask_agent(request: QueryRequest):
    user_query = request.query

    resolved_date = parse_date(user_query)
    if resolved_date:
        user_query = user_query.lower()
        user_query = user_query.replace("today", resolved_date)
        user_query = user_query.replace("tomorrow", resolved_date)

        for day in ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]:
            user_query = user_query.replace(day, resolved_date)

    response = agent.invoke({
        "messages": [
            ("system", system_message),
            ("user", user_query)
        ]
    })
    content = response["messages"][-1].content

    return {"response": content}
