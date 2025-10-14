from langgraph.prebuilt import create_react_agent
from app.services.llm_service import get_llm
from app.tools.helper_tools import (
    create_event_tool,
    list_events_tool,
    find_free_slots_tool,
    cancel_event_tool,
    reschedule_event_tool,
    check_conflict_tool,
    force_create_event_tool,
    reschedule_with_conflict_check_tool,
    force_reschedule_tool,
    schedule_multiple_meetings_tool,
    cancel_multiple_meetings_tool
)

def create_calendar_agent():
    llm = get_llm()
    
    tools = [
        check_conflict_tool,
        force_create_event_tool,
        create_event_tool,
        list_events_tool,
        find_free_slots_tool,
        cancel_event_tool,
        reschedule_with_conflict_check_tool,
        force_reschedule_tool,
        reschedule_event_tool,
        schedule_multiple_meetings_tool,
        cancel_multiple_meetings_tool
    ]
    
    agent = create_react_agent(llm, tools)
    return agent
