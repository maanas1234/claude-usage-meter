#!/usr/bin/env python3
"""WhatsApp bot via Twilio webhook. Deployed on Railway."""

import os
from dotenv import load_dotenv
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from agent import run

load_dotenv()

app = Flask(__name__)

# In-memory per-user conversation history  {whatsapp_number: [messages]}
conversations: dict[str, list] = {}

HELP_TEXT = (
    "Todoist Agent ready. Examples:\n\n"
    "• Schedule 30 system design videos in July, weekdays at 7pm\n"
    "• Add daily leetcode at 9am for 2 weeks, high priority\n"
    "• What's due today?\n"
    "• Delete all overdue tasks\n\n"
    "Send 'clear' to reset the conversation."
)


@app.route("/webhook", methods=["POST"])
def webhook():
    sender = request.form.get("From", "unknown")
    body   = request.form.get("Body", "").strip()

    resp = MessagingResponse()

    if not body:
        return str(resp)

    if body.lower() in ("hi", "hello", "start", "/start"):
        resp.message(HELP_TEXT)
        return str(resp)

    if body.lower() in ("clear", "/clear"):
        conversations[sender] = []
        resp.message("Conversation cleared.")
        return str(resp)

    if sender not in conversations:
        conversations[sender] = []

    conversations[sender].append({"role": "user", "content": body})

    try:
        conversations[sender], reply = run(conversations[sender], log=print)
        resp.message(reply or "Done.")
    except Exception as e:
        conversations[sender].pop()
        resp.message(f"Error: {e}")

    return str(resp)


@app.route("/health")
def health():
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
