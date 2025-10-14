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
    - "10am till 12pm"
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
def reschedule_event_tool(old_title: str, old_date: str, new_date: str, new_time: str = "", end_time: str = None):
    """
    **DEPRECATED TOOL** - This is a legacy function without conflict detection.
    Use reschedule_with_conflict_check_tool instead for proper conflict handling.
    """
    print(f"⚠️ DEPRECATED: reschedule_event_tool called: {old_title} from {old_date} to {new_date} at {new_time or 'same time'}-{end_time or ''}")
    print("⚠️ WARNING: This tool does not check for conflicts. Use reschedule_with_conflict_check_tool instead.")
    
    # Normalize dates (handles 'today', 'tomorrow', 'next Monday', etc.)
    if not re.match(r"\d{4}-\d{2}-\d{2}", old_date):
        old_date = calendar_tools.parse_date(old_date)
    if not re.match(r"\d{4}-\d{2}-\d{2}", new_date):
        new_date = calendar_tools.parse_date(new_date)
    
    # Just delegate to calendar_tools
    return calendar_tools.reschedule_event(old_title, old_date, new_date, new_time, end_time)


@tool
def check_conflict_tool(title: str, date: str, time: str):
    """
    Check for scheduling conflicts before creating an event.
    """
    print(f"⚡ check_conflict_tool called: {title} on {date} at {time}")
    
    try:
        # Parse date if needed
        if not re.match(r"\d{4}-\d{2}-\d{2}", date):
            date = calendar_tools.parse_date(date)
            print(f"📅 Parsed date: {date}")
        
        # Parse time range - try with and without "at" prefix
        start_time, end_time = calendar_tools.parse_time_range(time)
        if not start_time:
            # Try adding "at" prefix if it's missing
            start_time, end_time = calendar_tools.parse_time_range(f"at {time}")
        
        print(f"⏰ Parsed time: {start_time} to {end_time}")
        
        if not start_time:
            return f"❌ Could not parse time format: '{time}'. Please use formats like '3pm to 6pm', 'at 3pm for 3 hours', or 'at 3pm'."
        
        # Check for conflicts and create event
        result = calendar_tools.create_event_with_conflict_check(title, date, start_time, end_time)
        print(f"✅ Conflict check result: {result[:100]}...")
        return result
        
    except Exception as e:
        error_msg = f"❌ Error in conflict detection: {str(e)}"
        print(f"🚨 {error_msg}")
        return error_msg


@tool
def force_create_event_tool(title: str, date: str, time: str):
    """
    Force create an event even if there are conflicts.
    """
    print(f"⚡ force_create_event_tool called: {title} on {date} at {time}")
    
    try:
        # Parse date if needed
        if not re.match(r"\d{4}-\d{2}-\d{2}", date):
            date = calendar_tools.parse_date(date)
            print(f"📅 Parsed date: {date}")
        
        # Parse time range
        start_time, end_time = calendar_tools.parse_time_range(time)
        print(f"⏰ Parsed time: {start_time} to {end_time}")
        
        if not start_time:
            return f"❌ Could not parse time format: '{time}'. Please use formats like '3pm to 6pm', 'at 3pm for 3 hours', or 'at 3pm'."
        
        # Force create event
        result = calendar_tools.create_event_with_conflict_check(title, date, start_time, end_time, force=True)
        print(f"✅ Force create result: {result[:100]}...")
        return result
        
    except Exception as e:
        error_msg = f"❌ Error in force create: {str(e)}"
        print(f"🚨 {error_msg}")
        return error_msg


@tool
def reschedule_with_conflict_check_tool(old_title: str, old_date: str, new_date: str, new_time: str = "", end_time: str = None):
    """
    Reschedule events with conflict detection and available slot suggestions.
    """
    print(f"⚡ reschedule_with_conflict_check_tool called: {old_title} from {old_date} to {new_date} at {new_time or 'same time'}")
    
    try:
        # Parse dates if needed
        if not re.match(r"\d{4}-\d{2}-\d{2}", old_date):
            old_date = calendar_tools.parse_date(old_date)
            print(f"📅 Parsed old_date: {old_date}")
        
        if not re.match(r"\d{4}-\d{2}-\d{2}", new_date):
            new_date = calendar_tools.parse_date(new_date)
            print(f"📅 Parsed new_date: {new_date}")
        
        # Call the conflict-aware reschedule function
        result = calendar_tools.reschedule_event_with_conflict_check(old_title, old_date, new_date, new_time, end_time)
        print(f"✅ Reschedule with conflict check result: {result[:100]}...")
        return result
        
    except Exception as e:
        error_msg = f"❌ Error in reschedule with conflict check: {str(e)}"
        print(f"🚨 {error_msg}")
        return error_msg


@tool
def force_reschedule_tool(old_title: str, old_date: str, new_date: str, new_time: str = "", end_time: str = None):
    """
    Force reschedule events despite conflicts.
    """
    print(f"⚡ force_reschedule_tool called: {old_title} from {old_date} to {new_date} at {new_time or 'same time'}")
    
    try:
        # Parse dates if needed
        if not re.match(r"\d{4}-\d{2}-\d{2}", old_date):
            old_date = calendar_tools.parse_date(old_date)
            print(f"📅 Parsed old_date: {old_date}")
        
        if not re.match(r"\d{4}-\d{2}-\d{2}", new_date):
            new_date = calendar_tools.parse_date(new_date)
            print(f"📅 Parsed new_date: {new_date}")
        
        # Call the force reschedule function
        result = calendar_tools.force_reschedule_event(old_title, old_date, new_date, new_time, end_time)
        print(f"✅ Force reschedule result: {result[:100]}...")
        return result
        
    except Exception as e:
        error_msg = f"❌ Error in force reschedule: {str(e)}"
        print(f"🚨 {error_msg}")
        return error_msg


@tool
def schedule_multiple_meetings_tool(query: str):
    """
    Schedule multiple meetings from a single request with conflict detection.
    """
    print(f"⚡ schedule_multiple_meetings_tool called: {query}")
    
    try:
        # Parse multiple meetings from the query
        meetings = calendar_tools.parse_multiple_meetings(query)
        
        if not meetings:
            return "❌ Could not parse multiple meetings from the request. Please try separate requests for each meeting."
        
        # Convert to JSON string for the function
        import json
        meetings_data = json.dumps(meetings)
        
        # Call the multi-meeting scheduling function
        result = calendar_tools.schedule_multiple_meetings(meetings_data)
        print(f"✅ Multi-meeting schedule result: {result[:100]}...")
        return result
        
    except Exception as e:
        error_msg = f"❌ Error in multi-meeting schedule: {str(e)}"
        print(f"🚨 {error_msg}")
        return error_msg


@tool
def cancel_multiple_meetings_tool(query: str):
    """
    Cancel multiple specific meetings from a single request.
    """
    print(f"⚡ cancel_multiple_meetings_tool called: {query}")
    
    try:
        # Parse multiple cancellations from the query
        meetings = calendar_tools.parse_multiple_cancellations(query)
        
        if not meetings:
            return "❌ Could not parse multiple meeting cancellations from the request. Please try separate requests for each meeting."
        
        # Convert to JSON string for the function
        import json
        meetings_data = json.dumps(meetings)
        
        # Call the multi-meeting cancellation function
        result = calendar_tools.cancel_multiple_meetings(meetings_data)
        print(f"✅ Multi-meeting cancel result: {result[:100]}...")
        return result
        
    except Exception as e:
        error_msg = f"❌ Error in multi-meeting cancel: {str(e)}"
        print(f"🚨 {error_msg}")
        return error_msg