from datetime import datetime, timedelta, timezone
from app.services.google_calendar_service import get_calendar_service
from typing import List, Tuple, Optional
import re

# --- Date Parsing Function (unchanged) ---
def parse_date(query: str) -> str:
    today = datetime.today()
    query_lower = query.lower()

    if "today" in query_lower:
        return today.strftime("%Y-%m-%d")
    if "tomorrow" in query_lower:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")

    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2,
        "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
    }

    for day, idx in weekdays.items():
        if day in query_lower:
            current_weekday = today.weekday()
            days_ahead = (idx - current_weekday) % 7
            # If it's the same day and no "next" specified, use today
            if days_ahead == 0 and "next" not in query_lower:
                return today.strftime("%Y-%m-%d")
            # If it's the same day but "next" is specified, go to next week
            elif days_ahead == 0 and "next" in query_lower:
                days_ahead = 7
            if "next" in query_lower and days_ahead != 7:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    return today.strftime("%Y-%m-%d")

def standardize_time(raw_time: str) -> str:
    raw_time = raw_time.strip().replace(" ", "")
    try:
        # If it's just a number (like "10" or "25"), it's likely a parsing error
        if raw_time.isdigit():
            hour = int(raw_time)
            if hour > 23:
                print(f"Warning: Invalid hour {hour}, defaulting to 1:00")
                return "01:00"
            return f"{hour:02d}:00"
        
        if "am" in raw_time.lower() or "pm" in raw_time.lower():
            # Try different AM/PM formats
            formats = ["%I:%M%p", "%I%p", "%I:%M %p", "%I %p"]
            for fmt in formats:
                try:
                    dt = datetime.strptime(raw_time, fmt)
                    return dt.strftime("%H:%M")
                except ValueError:
                    continue
            # If no format works, try manual parsing
            hour_match = re.search(r'(\d{1,2})', raw_time)
            if hour_match:
                hour = int(hour_match.group(1))
                if 'pm' in raw_time.lower() and hour != 12:
                    hour += 12
                elif 'am' in raw_time.lower() and hour == 12:
                    hour = 0
                return f"{hour:02d}:00"
        else:
            # Try 24-hour format
            dt = datetime.strptime(raw_time, "%H:%M")
            return dt.strftime("%H:%M")
    except Exception as e:
        print(f"Error in standardize_time: {e}, input: {raw_time}")
        return "01:00"  # fallback to 1:00 AM


def parse_time_range(query: str):
    query = query.lower()

    # "10am to 12pm"
    match = re.search(r"(\d{1,2}(:\d{2})?\s?(am|pm)?)\s*(to|till|until|-)\s*(\d{1,2}(:\d{2})?\s?(am|pm)?)", query)
    if match:
        start_raw, end_raw = match.group(1), match.group(5)
        return standardize_time(start_raw), standardize_time(end_raw)

    # "at 9am for 2 hours"
    match = re.search(r"at\s+(\d{1,2}(:\d{2})?\s?(am|pm)?)\s+for\s+(\d+)\s*hour", query)
    if match:
        start_raw, hours = match.group(1), int(match.group(4))
        start_time = standardize_time(start_raw)
        dt = datetime.strptime(start_time, "%H:%M")
        end_time = (dt + timedelta(hours=hours)).strftime("%H:%M")
        return start_time, end_time

    # single time "at 5pm"
    match = re.search(r"at\s+(\d{1,2}(:\d{2})?\s?(am|pm)?)", query)
    if match:
        start_raw = match.group(1)
        start_time = standardize_time(start_raw)
        dt = datetime.strptime(start_time, "%H:%M")
        end_time = (dt + timedelta(hours=1)).strftime("%H:%M")
        return start_time, end_time

    return None, None


# --- CREATE EVENT ---
def create_event(title: str, date: str, start_time: str, end_time: str = None):
    service = get_calendar_service()
    
    start_datetime = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
    if end_time:
        end_datetime = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
    else:
        end_datetime = start_datetime + timedelta(hours=1)  # default

    event = {
        "summary": title,
        "start": {"dateTime": start_datetime.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_datetime.isoformat(), "timeZone": "UTC"},
    }

    service.events().insert(calendarId="primary", body=event).execute()
    return f"✅ Meeting '{title}' scheduled on {date} from {start_time} to {end_time or end_datetime.strftime('%H:%M')}."

# --- LIST EVENTS ---
def list_events(date: str):
    service = get_calendar_service()
    start_of_day = datetime.strptime(date, "%Y-%m-%d")
    end_of_day = start_of_day + timedelta(days=1)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_of_day.isoformat() + "Z",
        timeMax=end_of_day.isoformat() + "Z",
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])
    if not events:
        return f"📅 You have no events on {date}."

    lines = []
    for e in events:
        start_time = e["start"].get("dateTime", e["start"].get("date"))
        dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        lines.append(f"- {e['summary']} at {dt.strftime('%H:%M')}")

    return f"📅 Your schedule for {date}:\n" + "\n".join(lines)


# --- FIND FREE SLOTS ---
def find_free_slots(date: str):
    """
    Find free time slots on a given date (YYYY-MM-DD).
    Shows 1-hour slots from 9 AM to 6 PM.
    """
    service = get_calendar_service()
    start_of_day = datetime.strptime(date, "%Y-%m-%d")
    end_of_day = start_of_day + timedelta(days=1)
    
    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_of_day.isoformat() + "Z",
        timeMax=end_of_day.isoformat() + "Z",
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    
    events = events_result.get("items", [])
    
    # Define working hours (9 AM to 6 PM) with timezone awareness
    working_start = start_of_day.replace(hour=9, minute=0, tzinfo=timezone.utc)
    working_end = start_of_day.replace(hour=18, minute=0, tzinfo=timezone.utc)
    
    # Get all booked time slots
    booked_slots = []
    for event in events:
        event_start_str = event["start"].get("dateTime")
        event_end_str = event["end"].get("dateTime")
        
        if event_start_str and event_end_str:
            event_start = datetime.fromisoformat(event_start_str.replace("Z", "+00:00"))
            event_end = datetime.fromisoformat(event_end_str.replace("Z", "+00:00"))
            booked_slots.append((event_start, event_end))
    
    # Find available 1-hour slots
    available_slots = []
    current_time = working_start
    
    while current_time + timedelta(hours=1) <= working_end:
        slot_end = current_time + timedelta(hours=1)
        
        # Check if this slot conflicts with any booked events
        has_conflict = False
        for booked_start, booked_end in booked_slots:
            if (current_time < booked_end and slot_end > booked_start):
                has_conflict = True
                break
        
        if not has_conflict:
            available_slots.append(f"{current_time.strftime('%H:%M')}-{slot_end.strftime('%H:%M')}")
        
        current_time += timedelta(hours=1)  # Check every hour
    
    if not available_slots:
        return f"No free slots available on {date}."
    
    return f"🕒 Free slots on {date}: {', '.join(available_slots)}"


# --- CANCEL EVENTS ---
def cancel_event(title: str, date: str):
    service = get_calendar_service()
    start_of_day = datetime.strptime(date, "%Y-%m-%d")
    end_of_day = start_of_day + timedelta(days=1)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_of_day.isoformat() + "Z",
        timeMax=end_of_day.isoformat() + "Z",
        singleEvents=True
    ).execute()

    events = events_result.get("items", [])
    cancelled = []
    for e in events:
        if title.lower() in e["summary"].lower() or title.lower() in ["all", "everything"]:
            service.events().delete(calendarId="primary", eventId=e["id"]).execute()
            cancelled.append(e["summary"])
    
    if cancelled:
        return f"✅ Cancelled {len(cancelled)} event(s): {', '.join(cancelled)}"
    return f"⚠️ No meeting(s) found for '{title}' on {date}."

# --- RESCHEDULE EVENTS ---
def reschedule_event(old_title: str, old_date: str, new_date: str, new_time: str = "", end_time: str = None):
    """
    Reschedules one or multiple events.
    Handles:
    - "all" or specific event titles
    - relative or absolute dates
    - same time if no time specified
    - duration preservation if applicable
    """

    service = get_calendar_service()
    start_of_day = datetime.strptime(old_date, "%Y-%m-%d")
    end_of_day = start_of_day + timedelta(days=1)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_of_day.isoformat() + "Z",
        timeMax=end_of_day.isoformat() + "Z",
        singleEvents=True
    ).execute()

    events = events_result.get("items", [])
    if not events:
        return f"⚠️ No events found on {old_date}."

    # Filter target events
    target_events = [
        e for e in events
        if is_all_meetings_request(old_title) or old_title.lower() in e["summary"].lower()
    ]
    if not target_events:
        return f"⚠️ No matching events for '{old_title}' found on {old_date}."

    updated = []
    for e in target_events:
        start_str = e["start"].get("dateTime")
        end_str = e["end"].get("dateTime")
        if not start_str or not end_str:
            continue

        start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        duration = end_dt - start_dt

        # --- Time Handling ---
        if not new_time or new_time.lower() in ["same", "same time", ""]:
            # keep same start time
            new_start = datetime.strptime(f"{new_date} {start_dt.strftime('%H:%M')}", "%Y-%m-%d %H:%M")
            new_end = new_start + duration
        else:
            # normalize time (e.g., “3pm” → “15:00”)
            from app.tools.calendar_tools import standardize_time
            new_start_time = standardize_time(new_time)

            if end_time:
                new_end_time = standardize_time(end_time)
                new_start = datetime.strptime(f"{new_date} {new_start_time}", "%Y-%m-%d %H:%M")
                new_end = datetime.strptime(f"{new_date} {new_end_time}", "%Y-%m-%d %H:%M")
            else:
                new_start = datetime.strptime(f"{new_date} {new_start_time}", "%Y-%m-%d %H:%M")
                new_end = new_start + duration

        # --- Apply Update ---
        e["start"]["dateTime"] = new_start.isoformat()
        e["end"]["dateTime"] = new_end.isoformat()
        service.events().update(calendarId="primary", eventId=e["id"], body=e).execute()
        updated.append(e["summary"])

    if updated:
        if is_all_meetings_request(old_title):
            if not new_time:
                return f"✅ Rescheduled {len(updated)} event(s) from {old_date} to {new_date} (kept same times)."
            return f"✅ Rescheduled {len(updated)} event(s) from {old_date} to {new_date} at {new_time}."
        else:
            return f"✅ Rescheduled '{old_title}' from {old_date} to {new_date} ({'same time' if not new_time else new_time})."

    return f"⚠️ Could not reschedule any events from {old_date}."


def is_all_meetings_request(title: str) -> bool:
    """
    Check if the title indicates user wants to reschedule all meetings.
    Handles any variation like: all meetings, every meeting, all my meetings, etc.
    """
    title_lower = title.lower().strip()
    
    # Keywords that indicate "all meetings"
    all_keywords = ["all", "every", "everything", "entire", "each"]
    meeting_keywords = ["meeting", "meetings", "event", "events", "appointment", "appointments"]
    
    # Check if title contains any "all" keyword as a whole word or at the beginning
    has_all_keyword = any(
        title_lower == keyword or 
        title_lower.startswith(keyword + " ") or 
        title_lower.startswith(keyword + "s ") or
        " " + keyword + " " in title_lower or
        title_lower.endswith(" " + keyword)
        for keyword in all_keywords
    )
    
    # Check if title contains any "meeting" keyword
    has_meeting_keyword = any(keyword in title_lower for keyword in meeting_keywords)
    
    # Return True if:
    # 1. It has "all" keyword (like "all", "everything", "every")
    # 2. OR it has both "all" and "meeting" keywords (like "all meetings", "every meeting")
    return has_all_keyword and (not has_meeting_keyword or has_meeting_keyword)


def reschedule_event_with_conflict_check(old_title: str, old_date: str, new_date: str, new_time: str = "", end_time: str = None):
    """
    Reschedules one or multiple events with conflict detection and available slot suggestions.
    Handles:
    - "all" or specific event titles
    - relative or absolute dates
    - same time if no time specified
    - duration preservation if applicable
    - conflict detection with available slot suggestions
    """
    service = get_calendar_service()
    start_of_day = datetime.strptime(old_date, "%Y-%m-%d")
    end_of_day = start_of_day + timedelta(days=1)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_of_day.isoformat() + "Z",
        timeMax=end_of_day.isoformat() + "Z",
        singleEvents=True
    ).execute()

    events = events_result.get("items", [])
    if not events:
        return f"⚠️ No events found on {old_date}."

    # Filter target events
    target_events = [
        e for e in events
        if is_all_meetings_request(old_title) or old_title.lower() in e["summary"].lower()
    ]
    if not target_events:
        return f"⚠️ No matching events for '{old_title}' found on {old_date}."

    # Check for conflicts before rescheduling
    conflicts = []
    successful_reschedules = []
    
    for e in target_events:
        start_str = e["start"].get("dateTime")
        end_str = e["end"].get("dateTime")
        if not start_str or not end_str:
            continue

        start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        duration = end_dt - start_dt

        # Calculate new time
        if not new_time or new_time.lower() in ["same", "same time", ""]:
            new_start = datetime.strptime(f"{new_date} {start_dt.strftime('%H:%M')}", "%Y-%m-%d %H:%M")
            new_end = new_start + duration
        else:
            # Parse new time
            new_start_time = standardize_time(new_time)
            new_start = datetime.strptime(f"{new_date} {new_start_time}", "%Y-%m-%d %H:%M")
            new_end = new_start + duration

        # Check for conflicts
        has_conflict, conflicting_events = check_scheduling_conflict(
            new_date, 
            new_start.strftime("%H:%M"), 
            new_end.strftime("%H:%M")
        )
        
        if has_conflict:
            # Get available slots for this event's duration
            duration_hours = int(duration.total_seconds() / 3600)
            available_slots = get_available_slots(new_date, duration_hours)
            
            conflicts.append({
                "event": e["summary"],
                "old_time": f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}",
                "new_time": f"{new_start.strftime('%H:%M')}-{new_end.strftime('%H:%M')}",
                "conflicts": conflicting_events,
                "available_slots": available_slots
            })
        else:
            # No conflict - proceed with reschedule
            e["start"]["dateTime"] = new_start.isoformat()
            e["end"]["dateTime"] = new_end.isoformat()
            service.events().update(calendarId="primary", eventId=e["id"], body=e).execute()
            successful_reschedules.append(e["summary"])

    # Handle conflicts with available slot suggestions
    if conflicts:
        conflict_message = f"⚠️ Reschedule conflicts detected for {len(conflicts)} event(s):\n\n"
        
        for i, conflict in enumerate(conflicts, 1):
            conflict_message += f"{i}. **{conflict['event']}** ({conflict['old_time']} → {conflict['new_time']})\n"
            conflict_message += f"   Conflicts with:\n"
            for c in conflict['conflicts']:
                conflict_message += f"   - {c['title']} ({c['start']}-{c['end']})\n"
            
            # Show available slots for this event
            if conflict['available_slots']:
                conflict_message += f"   Available slots on {new_date}:\n"
                for slot in conflict['available_slots']:
                    conflict_message += f"   - {slot}\n"
            else:
                conflict_message += f"   No available slots found on {new_date}.\n"
            conflict_message += "\n"
        
        if successful_reschedules:
            conflict_message += f"✅ Successfully rescheduled: {', '.join(successful_reschedules)}\n\n"
        
        conflict_message += f"**Options:**\n"
        conflict_message += f"- Say 'Force reschedule' to reschedule despite conflicts\n"
        conflict_message += f"- Say 'Reschedule [event name] at [time slot]' to pick specific times\n"
        conflict_message += f"- Say 'Reschedule all at [time slot]' to reschedule all at the same time\n"
        
        return conflict_message

    # All reschedules successful
    if successful_reschedules:
        return f"✅ Successfully rescheduled {len(successful_reschedules)} event(s): {', '.join(successful_reschedules)}"
    
    return f"⚠️ No events were rescheduled."


def force_reschedule_event(old_title: str, old_date: str, new_date: str, new_time: str = "", end_time: str = None):
    """
    Force reschedule events even if there are conflicts.
    """
    service = get_calendar_service()
    start_of_day = datetime.strptime(old_date, "%Y-%m-%d")
    end_of_day = start_of_day + timedelta(days=1)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_of_day.isoformat() + "Z",
        timeMax=end_of_day.isoformat() + "Z",
        singleEvents=True
    ).execute()

    events = events_result.get("items", [])
    if not events:
        return f"⚠️ No events found on {old_date}."

    # Filter target events
    target_events = [
        e for e in events
        if is_all_meetings_request(old_title) or old_title.lower() in e["summary"].lower()
    ]
    if not target_events:
        return f"⚠️ No matching events for '{old_title}' found on {old_date}."

    updated = []
    for e in target_events:
        start_str = e["start"].get("dateTime")
        end_str = e["end"].get("dateTime")
        if not start_str or not end_str:
            continue

        start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        duration = end_dt - start_dt

        # Calculate new time
        if not new_time or new_time.lower() in ["same", "same time", ""]:
            new_start = datetime.strptime(f"{new_date} {start_dt.strftime('%H:%M')}", "%Y-%m-%d %H:%M")
            new_end = new_start + duration
        else:
            # Parse new time
            new_start_time = standardize_time(new_time)
            new_start = datetime.strptime(f"{new_date} {new_start_time}", "%Y-%m-%d %H:%M")
            new_end = new_start + duration

        # Force reschedule without conflict checking
        e["start"]["dateTime"] = new_start.isoformat()
        e["end"]["dateTime"] = new_end.isoformat()
        service.events().update(calendarId="primary", eventId=e["id"], body=e).execute()
        updated.append(e["summary"])

    if updated:
        return f"✅ Force rescheduled {len(updated)} event(s) from {old_date} to {new_date} despite conflicts: {', '.join(updated)}"
    
    return f"⚠️ No events were rescheduled."


# --- CONFLICT DETECTION FUNCTIONS ---
def check_scheduling_conflict(date: str, start_time: str, end_time: str) -> Tuple[bool, List[dict]]:
    """
    Check if there's a scheduling conflict for the given time slot.
    Returns (has_conflict, conflicting_events)
    """
    
    service = get_calendar_service()
    start_of_day = datetime.strptime(date, "%Y-%m-%d")
    end_of_day = start_of_day + timedelta(days=1)
    
    # Parse the requested time slot with timezone awareness
    # First standardize the time format to handle AM/PM
    standardized_start = standardize_time(start_time)
    standardized_end = standardize_time(end_time)
    
    requested_start = datetime.strptime(f"{date} {standardized_start}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    requested_end = datetime.strptime(f"{date} {standardized_end}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    
    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_of_day.isoformat() + "Z",
        timeMax=end_of_day.isoformat() + "Z",
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    
    events = events_result.get("items", [])
    conflicting_events = []
    
    for event in events:
        event_start_str = event["start"].get("dateTime")
        event_end_str = event["end"].get("dateTime")
        
        if event_start_str and event_end_str:
            event_start = datetime.fromisoformat(event_start_str.replace("Z", "+00:00"))
            event_end = datetime.fromisoformat(event_end_str.replace("Z", "+00:00"))
            
            # Check for overlap (now both are timezone-aware)
            if (requested_start < event_end and requested_end > event_start):
                conflicting_events.append({
                    "title": event["summary"],
                    "start": event_start.strftime("%H:%M"),
                    "end": event_end.strftime("%H:%M")
                })
    
    return len(conflicting_events) > 0, conflicting_events


def get_available_slots(date: str, duration_hours: int = 2) -> List[str]:
    """
    Get available time slots for a given duration on a specific date.
    """
    
    service = get_calendar_service()
    start_of_day = datetime.strptime(date, "%Y-%m-%d")
    end_of_day = start_of_day + timedelta(days=1)
    
    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_of_day.isoformat() + "Z",
        timeMax=end_of_day.isoformat() + "Z",
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    
    events = events_result.get("items", [])
    
    # Define working hours (9 AM to 6 PM) with timezone awareness
    working_start = start_of_day.replace(hour=9, minute=0, tzinfo=timezone.utc)
    working_end = start_of_day.replace(hour=18, minute=0, tzinfo=timezone.utc)
    
    # Get all booked time slots
    booked_slots = []
    for event in events:
        event_start_str = event["start"].get("dateTime")
        event_end_str = event["end"].get("dateTime")
        
        if event_start_str and event_end_str:
            event_start = datetime.fromisoformat(event_start_str.replace("Z", "+00:00"))
            event_end = datetime.fromisoformat(event_end_str.replace("Z", "+00:00"))
            booked_slots.append((event_start, event_end))
    
    # Find available slots
    available_slots = []
    current_time = working_start
    
    while current_time + timedelta(hours=duration_hours) <= working_end:
        slot_end = current_time + timedelta(hours=duration_hours)
        
        # Check if this slot conflicts with any booked events
        has_conflict = False
        for booked_start, booked_end in booked_slots:
            if (current_time < booked_end and slot_end > booked_start):
                has_conflict = True
                break
        
        if not has_conflict:
            available_slots.append(f"{current_time.strftime('%H:%M')}-{slot_end.strftime('%H:%M')}")
        
        current_time += timedelta(hours=1)  # Check every hour
    
    return available_slots[:5]  # Return max 5 options


def create_event_with_conflict_check(title: str, date: str, start_time: str, end_time: str = None, force: bool = False):
    """
    Create an event with conflict detection. If force=True, creates despite conflicts.
    """
    try:
        if not end_time:
            # Standardize time format first
            standardized_start = standardize_time(start_time)
            start_dt = datetime.strptime(f"{date} {standardized_start}", "%Y-%m-%d %H:%M")
            end_time = (start_dt + timedelta(hours=1)).strftime("%H:%M")
        
        if not force:
            has_conflict, conflicting_events = check_scheduling_conflict(date, start_time, end_time)
            
            if has_conflict:
                conflict_message = f"⚠️ Scheduling conflict detected.\n"
                for event in conflicting_events:
                    conflict_message += f"- {event['title']} ({event['start']}-{event['end']})\n"
                
                # Get available slots - standardize times first
                standardized_start = standardize_time(start_time)
                standardized_end = standardize_time(end_time)
                duration = (datetime.strptime(standardized_end, "%H:%M") - datetime.strptime(standardized_start, "%H:%M")).total_seconds() / 3600
                available_slots = get_available_slots(date, int(duration))
                
                conflict_message += f"\nYou can say 'Schedule' to schedule at the same time, or choose one of these available slots:\n"
                for slot in available_slots:
                    conflict_message += f"- {slot}\n"
                
                return conflict_message
        
        # No conflict or force=True, proceed with creation
        return create_event(title, date, start_time, end_time)
        
    except Exception as e:
        return f"❌ Error creating event: {str(e)}"


# --- MULTI-MEETING PARSING FUNCTIONS ---
def parse_multiple_meetings(query: str) -> List[dict]:
    """
    Parse multiple meetings from a single request.
    Examples:
    - "Schedule meeting with Ali on Wednesday from 10:00AM till 1PM and Meeting with Zaha from 2PM till 3PM"
    - "Create Team Standup on Monday at 9AM and Project Review on Tuesday at 2PM"
    - "Schedule Meeting with Ali on Thursday from 10AM till 12PM, Standup with Team from 1PM till 3PM, Meeting with Ali at 5PM"
    """
    meetings = []
    
    # Pattern 1: Comma-separated meetings
    if "," in query:
        # Split by comma and parse each part
        parts = [part.strip() for part in query.split(",")]
        for part in parts:
            meeting = parse_single_meeting(part.strip())
            if meeting:
                meetings.append(meeting)
    
    # Pattern 2: "meeting A and meeting B"
    elif " and " in query.lower():
        parts = query.split(" and ")
        for part in parts:
            meeting = parse_single_meeting(part.strip())
            if meeting:
                meetings.append(meeting)
    
    # Pattern 3: Multiple "schedule" commands
    elif query.lower().count("schedule") > 1:
        # Split by "schedule" and parse each part
        parts = re.split(r'\bschedule\b', query, flags=re.IGNORECASE)
        for part in parts[1:]:  # Skip first empty part
            meeting = parse_single_meeting("schedule " + part.strip())
            if meeting:
                meetings.append(meeting)
    
    return meetings


def parse_single_meeting(query: str) -> dict:
    """
    Parse a single meeting from a query string.
    Enhanced to handle various formats including comma-separated meetings.
    """
    try:
        # Clean up the query
        query = query.strip()
        
        # Remove leading "schedule", "create", "meeting" if present
        query = re.sub(r'^(schedule|create|meeting)\s+', '', query, flags=re.IGNORECASE)
        
        # Extract title - more flexible patterns
        title_patterns = [
            r'^([^on]+?)(?:\s+on|\s+at|\s+from)',  # "Meeting with Ali on Thursday"
            r'^([^0-9]+?)(?:\s+\d)',  # "Standup with Team 1PM"
            r'^(.+?)(?:\s+from|\s+at)',  # "Meeting with Ali from 10AM"
        ]
        
        title = None
        for pattern in title_patterns:
            title_match = re.search(pattern, query, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                break
        
        if not title:
            return None
        
        # Extract date - look for day names or absolute dates
        date_patterns = [
            r'on\s+(\w+)',  # "on Thursday"
            r'(\w+day)',    # "Thursday"
            r'(\d{4}-\d{2}-\d{2})',  # "2025-10-15"
        ]
        
        date = None
        for pattern in date_patterns:
            date_match = re.search(pattern, query, re.IGNORECASE)
            if date_match:
                try:
                    date_str = date_match.group(1)
                    # Check if it's already in YYYY-MM-DD format
                    if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                        date = date_str
                    else:
                        date = parse_date(date_str)
                    break
                except:
                    continue
        
        # If no date found, try to use context or default to today
        if not date:
            # Look for date context in the original query or use today
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Extract time - enhanced patterns
        time_patterns = [
            # "from 10:00am till 1pm" or "from 10AM to 12PM"
            r'(?:from\s+)?(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\s*(?:till|to|-)\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))',
            # "at 5PM" (single time)
            r'at\s+(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))',
            # "1PM till 3PM" (without "from")
            r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\s*(?:till|to|-)\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))',
        ]
        
        time_str = None
        for pattern in time_patterns:
            time_match = re.search(pattern, query, re.IGNORECASE)
            if time_match:
                if len(time_match.groups()) == 2:
                    # Two times found (start and end)
                    start_time = time_match.group(1).strip()
                    end_time = time_match.group(2).strip()
                    time_str = f"{start_time} till {end_time}"
                else:
                    # Single time found
                    time_str = time_match.group(1).strip()
                break
        
        if not time_str:
            return None
        
        return {
            'title': title,
            'date': date,
            'time': time_str
        }
    except Exception as e:
        print(f"Error parsing single meeting: {e}")
        return None


def parse_multiple_cancellations(query: str) -> List[dict]:
    """
    Parse multiple meeting cancellations from a single request.
    Examples:
    - "delete meeting with Ali at 10AM and meeting with Zaha at 4PM"
    - "cancel Team Standup and Project Review on Monday"
    """
    meetings = []
    
    # Pattern 1: "delete A and B"
    if " and " in query.lower():
        parts = query.split(" and ")
        for part in parts:
            meeting = parse_single_cancellation(part.strip())
            if meeting:
                meetings.append(meeting)
    
    # Pattern 2: Multiple "delete/cancel" commands
    elif query.lower().count("delete") > 1 or query.lower().count("cancel") > 1:
        # Split by delete/cancel and parse each part
        parts = re.split(r'\b(delete|cancel)\b', query, flags=re.IGNORECASE)
        for i in range(1, len(parts), 2):  # Skip first empty part, take every other
            if i + 1 < len(parts):
                meeting = parse_single_cancellation(parts[i] + " " + parts[i + 1].strip())
                if meeting:
                    meetings.append(meeting)
    
    return meetings


def parse_single_cancellation(query: str) -> dict:
    """
    Parse a single meeting cancellation from a query string.
    """
    try:
        # Extract title and date from the query
        title_match = re.search(r'(?:meeting with|meeting|delete|cancel)\s+([^on]+?)(?:\s+on|\s+at|\s+from)', query, re.IGNORECASE)
        if not title_match:
            return None
            
        title = title_match.group(1).strip()
        
        # Extract date
        date_match = re.search(r'on\s+(\w+)', query, re.IGNORECASE)
        if date_match:
            date = parse_date(date_match.group(1))
        else:
            # Try to get date from context or use today
            date = datetime.now().strftime("%Y-%m-%d")
            
        return {
            'title': title,
            'date': date
        }
    except Exception as e:
        print(f"Error parsing single cancellation: {e}")
        return None


def calculate_duration(start_time: str, end_time: str) -> int:
    """
    Calculate duration in hours between start and end time.
    Handles various time formats including AM/PM.
    """
    try:
        # Normalize time strings to handle AM/PM format
        def normalize_time(time_str):
            time_str = time_str.strip().upper()
            # Remove extra spaces and handle various formats
            time_str = re.sub(r'\s+', ' ', time_str)
            
            # Try different time formats
            formats = [
                "%I:%M %p",  # 10:00 AM
                "%I %p",     # 10 AM
                "%H:%M",     # 10:00
                "%H",        # 10
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue
            
            # If no format works, try to extract just the hour
            hour_match = re.search(r'(\d{1,2})', time_str)
            if hour_match:
                hour = int(hour_match.group(1))
                if 'PM' in time_str and hour != 12:
                    hour += 12
                elif 'AM' in time_str and hour == 12:
                    hour = 0
                return datetime.strptime(f"{hour:02d}:00", "%H:%M")
            
            raise ValueError(f"Could not parse time: {time_str}")
        
        start_dt = normalize_time(start_time)
        end_dt = normalize_time(end_time)
        
        # Handle case where end time is next day
        if end_dt < start_dt:
            end_dt = end_dt.replace(day=end_dt.day + 1)
        
        duration = end_dt - start_dt
        return int(duration.total_seconds() / 3600)
    except Exception as e:
        print(f"Error calculating duration: {e}")
        return 1  # Default to 1 hour


def schedule_multiple_meetings(meetings_data: str):
    """
    Schedule multiple meetings from a single request with conflict detection.
    """
    try:
        import json
        meetings = json.loads(meetings_data)
        results = []
        conflicts = []
        
        for meeting in meetings:
            # Parse time to get start and end times
            time_str = meeting['time']
            if 'till' in time_str:
                start_time, end_time = time_str.split(' till ')
                start_time = start_time.strip()
                end_time = end_time.strip()
            else:
                start_time = time_str
                end_time = None
            
            # Check conflicts for each meeting
            has_conflict, conflicting_events = check_scheduling_conflict(
                meeting['date'], 
                start_time, 
                end_time
            )
            
            if has_conflict:
                # Get available slots for this event's duration
                if end_time:
                    duration_hours = calculate_duration(start_time, end_time)
                else:
                    duration_hours = 1  # Default 1 hour
                    
                available_slots = get_available_slots(meeting['date'], duration_hours)
                
                conflicts.append({
                    'meeting': meeting,
                    'conflicts': conflicting_events,
                    'available_slots': available_slots
                })
            else:
                # Schedule immediately if no conflict
                result = create_event(
                    meeting['title'],
                    meeting['date'],
                    meeting['time']
                )
                if "successfully created" in result.lower():
                    results.append(meeting['title'])
        
        # Handle conflicts
        if conflicts:
            conflict_message = f"⚠️ Scheduling conflicts detected for {len(conflicts)} meeting(s):\n\n"
            
            for i, conflict in enumerate(conflicts, 1):
                meeting = conflict['meeting']
                conflict_message += f"{i}. **{meeting['title']}** ({meeting['time']})\n"
                conflict_message += f"   Conflicts with:\n"
                for c in conflict['conflicts']:
                    conflict_message += f"   - {c['title']} ({c['start']}-{c['end']})\n"
                
                # Show available slots
                if conflict['available_slots']:
                    conflict_message += f"   Available slots on {meeting['date']}:\n"
                    for slot in conflict['available_slots']:
                        conflict_message += f"   - {slot}\n"
                conflict_message += "\n"
            
            if results:
                conflict_message += f"✅ Successfully scheduled: {', '.join(results)}\n\n"
            
            conflict_message += f"**Options:**\n"
            conflict_message += f"- Say 'Force schedule all' to schedule despite conflicts\n"
            conflict_message += f"- Say 'Schedule [meeting name] at [time slot]' to pick specific times\n"
            conflict_message += f"- Say 'Schedule all at [time slot]' to schedule all at the same time\n"
            
            return conflict_message
        
        # All meetings scheduled successfully
        return f"✅ Successfully scheduled {len(results)} meeting(s): {', '.join(results)}"
        
    except Exception as e:
        return f"❌ Error scheduling multiple meetings: {str(e)}"


def cancel_multiple_meetings(meetings_data: str):
    """
    Cancel multiple specific meetings from a single request.
    """
    try:
        import json
        meetings = json.loads(meetings_data)
        results = []
        not_found = []
        
        for meeting in meetings:
            # Try to cancel each meeting
            result = cancel_event(meeting['title'], meeting['date'])
            
            if "successfully cancelled" in result.lower():
                results.append(meeting['title'])
            else:
                not_found.append({
                    'title': meeting['title'],
                    'date': meeting['date'],
                    'reason': result
                })
        
        # Build response message
        if results and not_found:
            message = f"✅ Successfully cancelled: {', '.join(results)}\n"
            message += f"⚠️ Could not find: {', '.join([m['title'] for m in not_found])}"
        elif results:
            message = f"✅ Successfully cancelled {len(results)} meeting(s): {', '.join(results)}"
        elif not_found:
            message = f"⚠️ Could not find any of the specified meetings: {', '.join([m['title'] for m in not_found])}"
        else:
            message = "⚠️ No meetings were cancelled."
        
        return message
        
    except Exception as e:
        return f"❌ Error cancelling multiple meetings: {str(e)}"
