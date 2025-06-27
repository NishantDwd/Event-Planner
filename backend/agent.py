from datetime import datetime, timedelta
from calendar_utils import get_free_slots, book_event
from gemini_agent import extract_event_info
import dateparser
import re

# In-memory session state (for demo; use Redis/DB for production)
SESSION_STATE = {}

def parse_date(date_str):
    if not date_str:
        return None
    dt = dateparser.parse(date_str)
    return dt

def parse_duration(duration_str):
    if not duration_str:
        return 30  # default to 30 minutes
    if isinstance(duration_str, int):
        return duration_str
    if isinstance(duration_str, float):
        return int(duration_str)
    # Try to parse "HH:MM"
    match = re.match(r"^\s*(\d+):(\d+)\s*$", duration_str)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        return hours * 60 + minutes
     # Try to parse "X hours" or "X minutes"
    match = re.match(r"^\s*(\d+)\s*hours?", duration_str, re.IGNORECASE)
    if match:
        return int(match.group(1)) * 60
    match = re.match(r"^\s*(\d+)\s*minutes?", duration_str, re.IGNORECASE)
    if match:
        return int(match.group(1))
    # Try to parse as integer minutes
    try:
        return int(duration_str)
    except Exception:
        return 30  # fallback default
    
def extract_time_and_duration(time_str):
    """
    If time_str is a range like '8:00 PM - 9:00 PM', return ('8:00 PM', duration_in_minutes)
    If time_str is a single time, return (time_str, None)
    """
    if not time_str:
        return None, None
    parts = re.split(r"\s*-\s*", time_str)
    if len(parts) == 2:
        start_time, end_time = parts
        start_dt = dateparser.parse(start_time)
        end_dt = dateparser.parse(end_time)
        if start_dt and end_dt:
            duration = int((end_dt - start_dt).total_seconds() // 60)
            return start_time, duration
    return time_str, None

async def process_message(message, session_id):
    # Get or create session context
    context = SESSION_STATE.get(session_id, {})
    extracted = extract_event_info(message)
    intent = extracted.get("intent", "unknown")
    reason = extracted.get("reason", "")

    # Handle greetings/capabilities/reject/unknown
    if intent in ["greet", "capabilities", "reject", "unknown"]:
        return reason or "Sorry, I only assist with calendar event planning."

    # Update context with any new info
    for key in ["date", "time", "duration", "summary", "attendees"]:
        val = extracted.get(key)
        if val:
            context[key] = val

    # Save context
    SESSION_STATE[session_id] = context

    if intent == "book":
        date = context.get("date")
        time = context.get("time")
        duration = context.get("duration", 30)
        summary = context.get("summary")
        attendees = context.get("attendees", [])

        # Try to extract time and duration from time string if it's a range
        time, duration_from_range = extract_time_and_duration(time)
        if duration_from_range:
            duration = duration_from_range
        duration = parse_duration(duration)

        # Check for missing fields and prompt user
        if not date:
            return "For which date would you like to book the appointment?"
        if not time:
            return "What time should I book the meeting on?"
        if not summary:
            return "What should be the title or purpose of the meeting?"

        # Defensive: attendees must be a list of emails
        if attendees and not isinstance(attendees, list):
            # Try to extract emails from a string, or ignore if not possible
            import re
            found_emails = re.findall(r'[\w\.-]+@[\w\.-]+', str(attendees))
            attendees = found_emails if found_emails else []

        # Parse date and time robustly
        dt = parse_date(f"{date} {time}")
        if not dt:
            return "Please provide a valid date and time for the meeting."
        start = dt
        end = start + timedelta(minutes=duration)

        # Try/except for booking
        try:
            slots = get_free_slots('primary', start.replace(hour=0, minute=0), start.replace(hour=23, minute=59), duration)
            available = any(s[0] <= start < s[1] and (s[1] - start).total_seconds() >= duration*60 for s in slots)
            if not available:
                return f"Sorry, no free slot available at that time on {start.strftime('%Y-%m-%d')}."
            link = book_event('primary', start, end, summary, "Booked via AI assistant", attendees)
            # Clear session after booking
            SESSION_STATE.pop(session_id, None)
            return f"Your event '{summary}' has been booked for {start.strftime('%Y-%m-%d %H:%M')}! [View in Calendar]({link})"
        except Exception as e:
            return f"Sorry, there was an error booking your event: {str(e)}"    
    # Handle availability check

    if intent == "check_availability":
        date = context.get("date")
        duration = int(context.get("duration", 30))
        dt = parse_date(date)
        if not dt:
            return "For which date should I check availability?"
        start = dt.replace(hour=0, minute=0)
        end = start + timedelta(days=1)
        slots = get_free_slots('primary', start, end, duration)
        if not slots:
            return f"No free slots on {start.strftime('%Y-%m-%d')}."
        # Only show slots where end > start and format correctly
        slot_str = "\n".join([
            f"{s[0].strftime('%H:%M')} - {s[1].strftime('%H:%M')}"
            for s in slots if s[1] > s[0]
        ])
        if not slot_str:
            return f"No valid free slots on {start.strftime('%Y-%m-%d')}."
        return f"Available slots on {start.strftime('%Y-%m-%d')}:\n{slot_str}"

    # Handle reschedule/cancel (optional: implement as needed)
    if intent == "reschedule":
        return "Rescheduling is not yet implemented."
    if intent == "cancel":
        return "Canceling events is not yet implemented."

    return "How can I assist you with your calendar today?"