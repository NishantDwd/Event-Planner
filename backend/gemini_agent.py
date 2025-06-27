import re
import requests
import json

GEMINI_API_KEY = "Your-API-Key"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

def extract_event_info(user_message):
    prompt = f"""
You are a friendly AI assistant that ONLY helps users with Google Calendar event planning (checking availability, booking, rescheduling, or canceling events).

Always extract as many of these fields as possible from the user's message: date, time (or time range), duration, summary, attendees.
If the user provides a time range (like "8:00 PM - 9:00 PM"), set 'time' to the start time and 'duration' to the difference in minutes.
If any field is missing, leave it blank.

If the user's message is a greeting (like "hi", "hello", "hey there"), respond with:
{{
  "intent": "greet",
  "reason": "Hello! 👋 I’m your calendar assistant. I can help you check availability, book, reschedule, or cancel events on your Google Calendar. How can I assist you today?"
}}

If the user asks about your capabilities (like "what can you do?", "how can you help me?"), respond with:
{{
  "intent": "capabilities",
  "reason": "I can help you with: booking appointments, checking availability, rescheduling, or canceling events on your Google Calendar. Just tell me what you’d like to do!"
}}

If the user's request is unrelated to calendar events, respond with:
{{
  "intent": "reject",
  "reason": "Your request is not related to calendar event planning."
}}

Otherwise, extract the user's intent and all relevant details for a calendar event from the following message.
Respond in JSON with fields: intent (one of: book, check_availability, reschedule, cancel, greet, capabilities, unknown, reject), date, time, duration, attendees, summary, and reason (if intent is reject, greet, capabilities, or unknown).

Do NOT wrap your response in markdown or code blocks. Only output raw JSON.

Message: "{user_message}"
"""
    data = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }
    response = requests.post(GEMINI_API_URL, json=data)
    response.raise_for_status()
    text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    # Remove code block markers and whitespace if present
    text = re.sub(r"^```json|^```|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        # Try to extract JSON from within the text if Gemini returns extra text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        # Fallback: If Gemini returns plain text, wrap it as a friendly message
        return {"intent": "unknown", "reason": text if text else "Sorry, I could not understand your request."}
