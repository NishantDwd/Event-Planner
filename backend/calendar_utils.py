import os
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'service_account.json'  # Place your credentials here

def get_calendar_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=creds)
    return service

def get_free_slots(calendar_id, start, end, duration_minutes=30):
    service = get_calendar_service()
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=start.isoformat() + 'Z',
        timeMax=end.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    # Find free slots
    slots = []
    current = start
    for event in events:
        event_start = datetime.fromisoformat(event['start']['dateTime'][:-1])
        if (event_start - current).total_seconds() >= duration_minutes * 60:
            slots.append((current, event_start))
        current = datetime.fromisoformat(event['end']['dateTime'][:-1])
    if (end - current).total_seconds() >= duration_minutes * 60:
        slots.append((current, end))
    return slots

def book_event(calendar_id, start, end, summary, description, attendees=[]):
    service = get_calendar_service()
    event = {
        'summary': summary,
        'description': description,
        'start': {'dateTime': start.isoformat(), 'timeZone': 'UTC'},
        'end': {'dateTime': end.isoformat(), 'timeZone': 'UTC'},
        'attendees': [{'email': email} for email in attendees],
    }
    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
    return created_event.get('htmlLink')