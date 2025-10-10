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
            if days_ahead == 0:
                days_ahead = 7
            if "next" in query_lower:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    return today.strftime("%Y-%m-%d")

def standardize_time(raw_time: str) -> str:
    raw_time = raw_time.strip().replace(" ", "")
    try:
        if "am" in raw_time or "pm" in raw_time:
            dt = datetime.strptime(raw_time, "%I%p")
        else:
            dt = datetime.strptime(raw_time, "%H:%M")
        return dt.strftime("%H:%M")
    except Exception:
        return raw_time  # fallback


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
    all_slots = ["09:00", "11:00", "13:00", "15:00", "17:00"]
    events_result = list_events(date)
    
    if "no events" in events_result:
        return f"🕒 Free slots on {date}: {', '.join(all_slots)}"

    booked_slots = []
    for line in events_result.split("\n")[1:]:
        booked_slots.append(line.split(" at ")[1])

    free_slots = [s for s in all_slots if s not in booked_slots]
    if not free_slots:
        return f"No free slots available on {date}."
    return f"🕒 Free slots on {date}: {', '.join(free_slots)}"


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
        if old_title.lower() in ["all", "everything"] or old_title.lower() in e["summary"].lower()
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
        if old_title.lower() in ["all", "everything"]:
            if not new_time:
                return f"✅ Rescheduled {len(updated)} event(s) from {old_date} to {new_date} (kept same times)."
            return f"✅ Rescheduled {len(updated)} event(s) from {old_date} to {new_date} at {new_time}."
        else:
            return f"✅ Rescheduled '{old_title}' from {old_date} to {new_date} ({'same time' if not new_time else new_time})."

    return f"⚠️ Could not reschedule any events from {old_date}."


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
    requested_start = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    requested_end = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    
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
            start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
            end_time = (start_dt + timedelta(hours=1)).strftime("%H:%M")
        
        if not force:
            has_conflict, conflicting_events = check_scheduling_conflict(date, start_time, end_time)
            
            if has_conflict:
                conflict_message = f"⚠️ Scheduling conflict detected.\n"
                for event in conflicting_events:
                    conflict_message += f"- {event['title']} ({event['start']}-{event['end']})\n"
                
                # Get available slots
                duration = (datetime.strptime(end_time, "%H:%M") - datetime.strptime(start_time, "%H:%M")).total_seconds() / 3600
                available_slots = get_available_slots(date, int(duration))
                
                conflict_message += f"\nYou can say 'Schedule' to schedule at the same time, or choose one of these available slots:\n"
                for slot in available_slots:
                    conflict_message += f"- {slot}\n"
                
                return conflict_message
        
        # No conflict or force=True, proceed with creation
        return create_event(title, date, start_time, end_time)
        
    except Exception as e:
        return f"❌ Error creating event: {str(e)}"
