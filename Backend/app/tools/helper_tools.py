import re
from langchain_core.tools import tool
from app.tools import calendar_tools
from app.tools.calendar_tools import parse_time_range

# -------------------------
# Calendar Tools (LLM callable)
# -------------------------

@tool
def create_event_tool(title: str, date: str, time: str):
    """
    Create a calendar event. Supports:
    - "10am to 12pm"
    - "at 3pm for 2 hours"
    - "at 5pm" (defaults to 1 hour)
    """
    print(f"⚡ create_event_tool called: {title} on {date} at {time}")
    if not re.match(r"\d{4}-\d{2}-\d{2}", date):
        date = calendar_tools.parse_date(date)

    start_time, end_time = parse_time_range(time)
    if not start_time:
        start_time, end_time = time, None

    return calendar_tools.create_event(title, date, start_time, end_time)

@tool
def list_events_tool(date: str):
    """
    List all events on a given date (YYYY-MM-DD).
    """
    print(f"⚡ list_events_tool called: {date}")
    if not re.match(r"\d{4}-\d{2}-\d{2}", date):
        date = calendar_tools.parse_date(date)
    return calendar_tools.list_events(date)


@tool
def find_free_slots_tool(date: str):
    """
    Find free time slots on a given date (YYYY-MM-DD).
    """
    print(f"⚡ find_free_slots_tool called: {date}")
    if not re.match(r"\d{4}-\d{2}-\d{2}", date):
        date = calendar_tools.parse_date(date)
    return calendar_tools.find_free_slots(date)


@tool
def cancel_event_tool(title: str, date: str):
    """Cancel one or multiple events by title or all events on a date."""
    print(f"⚡ cancel_event_tool called: {title} on {date}")
    if not re.match(r"\d{4}-\d{2}-\d{2}", date):
        date = calendar_tools.parse_date(date)
    return calendar_tools.cancel_event(title, date)


@tool
def reschedule_event_tool(old_title: str, old_date: str, new_date: str, new_time: str, end_time: str = None):
    """Reschedule one or multiple events per day."""
    print(f"⚡ reschedule_event_tool called: {old_title} from {old_date} to {new_date} at {new_time}-{end_time}")
    if not re.match(r"\d{4}-\d{2}-\d{2}", old_date):
        old_date = calendar_tools.parse_date(old_date)
    if not re.match(r"\d{4}-\d{2}-\d{2}", new_date):
        new_date = calendar_tools.parse_date(new_date)
    return calendar_tools.reschedule_event(old_title, old_date, new_date, new_time, end_time)
