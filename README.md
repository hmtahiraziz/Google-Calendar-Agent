# AI Calendar Assistant – Smart Calendar Management

An AI-powered calendar assistant that integrates with Google Calendar.
It can create, list, reschedule, cancel events, and find free slots using natural language queries.

---

# Key Features

* Ask about your schedule using natural language
* Create events with flexible time formats ("10am to 12pm", "at 3pm for 2 hours", "at 5pm")
* List all events on a given date
* Find free time slots
* Reschedule or cancel events easily
* Built with LangChain + LLM agents (Google Gemini Pro)
* Supports conversational context for smarter responses

---

# How It Works

1. Connects to Google Calendar using OAuth2
2. Uses an LLM agent (LangChain + Google Gemini Pro) to understand natural language queries
3. Tools available for the agent:

   * Create events
   * List events
   * Find free slots
   * Cancel events
   * Reschedule events
4. The agent calls the appropriate tool based on your query and returns precise output

---

# Example Queries You Can Ask

* "What is my schedule on Friday?"
* "Create a meeting with John tomorrow at 5pm for 2 hours"
* "Cancel my meeting with Zach on Monday"
* "Reschedule my team meeting from Monday to Tuesday at 3pm"
* "Show me free slots on Thursday"

---

# Chatbot UI

<img width="1893" height="908" alt="Screenshot1" src="https://github.com/user-attachments/assets/5ecafd76-212b-424d-a267-50544bce50a1" />

<img width="1897" height="907" alt="Screeshot2" src="https://github.com/user-attachments/assets/def518fb-0df9-4e92-81c8-5e511cd22b26" />



# Getting Started

# Clone the repo

git clone https://github.com/hmtahiraziz/Google-Calendar-Agent.git

# Backend

cd Backend

# Install dependencies

pip install -r requirements.txt

# Run the backend

uvicorn app.main:app --reload

---

# Frontend

cd Frontend

# Install dependencies

npm install

# Run the frontend

npm run dev

---

# Tools Available

* create_event_tool(title, date, time): Create a calendar event
* list_events_tool(date): List all events on a given date (YYYY-MM-DD)
* find_free_slots_tool(date): Show free time slots
* cancel_event_tool(title, date): Cancel events by title or all events on a date
* reschedule_event_tool(old_title, old_date, new_date, new_time, end_time): Reschedule events

---


