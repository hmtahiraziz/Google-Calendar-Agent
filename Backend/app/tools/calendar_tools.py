from datetime import datetime, timedelta
from app.services.google_calendar_service import get_calendar_service
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
def reschedule_event(old_title: str, old_date: str, new_date: str, new_time: str, end_time: str = None):
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
    updated = []
    for e in events:
        if old_title.lower() in e["summary"].lower() or old_title.lower() in ["all", "everything"]:
            start_datetime = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
            end_datetime = datetime.strptime(f"{new_date} {end_time}", "%Y-%m-%d %H:%M") if end_time else start_datetime + timedelta(hours=1)

            e["start"]["dateTime"] = start_datetime.isoformat()
            e["end"]["dateTime"] = end_datetime.isoformat()
            service.events().update(calendarId="primary", eventId=e["id"], body=e).execute()
            updated.append(e["summary"])
    
    if updated:
        return f"✅ Rescheduled {len(updated)} event(s): {', '.join(updated)}"
    return f"⚠️ No meeting(s) titled '{old_title}' found on {old_date}."
