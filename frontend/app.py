import streamlit as st
import requests
import uuid

st.set_page_config(page_title="AI Calendar Booking Assistant", page_icon="📅", layout="centered")

st.title("📅 AI Calendar Booking Assistant")
st.markdown("Chat with the assistant to book or check your calendar availability.")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def send_message(message):
    url = "http://localhost:8000/chat"
    payload = {"message": message, "session_id": st.session_state.session_id}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "Sorry, I didn't get a valid response from the server.")
    except requests.exceptions.RequestException as e:
        return f"Network error: {e}"
    except ValueError:
        return "Sorry, the server returned an invalid response."

with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input("Type your message...", "")
    submitted = st.form_submit_button("Send")
    if submitted and user_input:
        st.session_state.chat_history.append(("user", user_input))
        response = send_message(user_input)
        st.session_state.chat_history.append(("assistant", response))

for sender, msg in st.session_state.chat_history:
    if sender == "user":
        st.markdown(f"**You:** {msg}")
    else:
        st.markdown(f"**Assistant:** {msg}")