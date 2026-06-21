#!/usr/bin/env python3
"""Todoist agent — DeepSeek via OpenRouter. CLI: python agent.py"""

import os
import sys
import json
from datetime import date
import requests

# force UTF-8 output so emoji in model replies don't crash on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

TODOIST_TOKEN  = os.environ.get("TODOIST_API_TOKEN")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY")

if not TODOIST_TOKEN:
    raise SystemExit("Missing TODOIST_API_TOKEN — set it in todoist-agent/.env")
if not OPENROUTER_KEY:
    raise SystemExit("Missing OPENROUTER_API_KEY — set it in todoist-agent/.env")

BASE  = "https://api.todoist.com/api/v1"
AUTH  = {"Authorization": f"Bearer {TODOIST_TOKEN}", "Content-Type": "application/json"}
MODEL = "deepseek/deepseek-v4-flash"

client = OpenAI(api_key=OPENROUTER_KEY, base_url="https://openrouter.ai/api/v1")

# ---------------------------------------------------------------------------
# Todoist API helpers  (v1 — GET returns {"results": [...], "next_cursor": ...})
# ---------------------------------------------------------------------------

def _get(path, params=None):
    r = requests.get(f"{BASE}{path}", headers=AUTH, params=params)
    r.raise_for_status()
    data = r.json()
    return data.get("results", data)   # unwrap pagination wrapper

def _post(path, body=None):
    r = requests.post(f"{BASE}{path}", headers=AUTH, json=body or {})
    r.raise_for_status()
    return r.json() if r.content else {"ok": True}

def _delete(path):
    r = requests.delete(f"{BASE}{path}", headers=AUTH)
    r.raise_for_status()
    return {"ok": True}


def get_projects(_):
    return _get("/projects")

def get_tasks(args):
    params = {}
    if args.get("project_id"): params["project_id"] = args["project_id"]
    if args.get("filter"):      params["filter"]     = args["filter"]
    return _get("/tasks", params)

def create_task(args):
    body = {k: v for k, v in args.items() if v is not None}
    return _post("/tasks", body)

def create_tasks_bulk(args):
    results = []
    for t in args["tasks"]:
        body = {k: v for k, v in t.items() if v is not None}
        results.append(_post("/tasks", body))
    return {"created": len(results), "tasks": results}

def update_task(args):
    task_id = args.pop("task_id")
    body = {k: v for k, v in args.items() if v is not None}
    return _post(f"/tasks/{task_id}", body)

def complete_task(args):
    return _post(f"/tasks/{args['task_id']}/close")

def delete_task(args):
    return _delete(f"/tasks/{args['task_id']}")

def add_reminder(args):
    """Requires Todoist Premium."""
    body = {"item_id": args["task_id"], "type": args["type"]}
    if args["type"] == "relative":
        body["minute_offset"] = args.get("minute_offset", 30)
    else:
        body["due"] = {"date": args["due_datetime"]}
    try:
        return _post("/reminders", body)
    except requests.HTTPError as e:
        if e.response.status_code in (403, 404):
            return {"error": "Reminders require Todoist Premium. Tasks with due times auto push-notify via the app."}
        raise


TOOL_FNS = {
    "get_projects":      get_projects,
    "get_tasks":         get_tasks,
    "create_task":       create_task,
    "create_tasks_bulk": create_tasks_bulk,
    "update_task":       update_task,
    "complete_task":     complete_task,
    "delete_task":       delete_task,
    "add_reminder":      add_reminder,
}

# ---------------------------------------------------------------------------
# Tool schemas (OpenAI / OpenRouter format)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_projects",
            "description": "List all Todoist projects with their IDs.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_tasks",
            "description": "Fetch tasks. Use Todoist filter strings: 'today', 'overdue', '#ProjectName', 'label:leetcode'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "filter": {"type": "string", "description": "e.g. 'today', 'overdue', '#Work & p1'"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a single task.",
            "parameters": {
                "type": "object",
                "required": ["content"],
                "properties": {
                    "content":     {"type": "string"},
                    "due_string":  {"type": "string", "description": "e.g. 'tomorrow at 7pm', 'Jun 25 at 8am'"},
                    "priority":    {"type": "integer", "enum": [1, 2, 3, 4], "description": "1=normal 2=medium 3=high 4=urgent"},
                    "project_id":  {"type": "string"},
                    "description": {"type": "string"},
                    "labels":      {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_tasks_bulk",
            "description": (
                "Create many tasks at once. Use for scheduling series like '30 videos over a month'. "
                "Each task needs an explicit due_string like 'Jun 23 2026 at 7pm'. "
                "Skip weekends by default unless told otherwise."
            ),
            "parameters": {
                "type": "object",
                "required": ["tasks"],
                "properties": {
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["content"],
                            "properties": {
                                "content":     {"type": "string"},
                                "due_string":  {"type": "string"},
                                "priority":    {"type": "integer", "enum": [1, 2, 3, 4]},
                                "project_id":  {"type": "string"},
                                "description": {"type": "string"},
                                "labels":      {"type": "array", "items": {"type": "string"}},
                            },
                        },
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_task",
            "description": "Update an existing task by ID.",
            "parameters": {
                "type": "object",
                "required": ["task_id"],
                "properties": {
                    "task_id":     {"type": "string"},
                    "content":     {"type": "string"},
                    "due_string":  {"type": "string"},
                    "priority":    {"type": "integer", "enum": [1, 2, 3, 4]},
                    "description": {"type": "string"},
                    "labels":      {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": "Mark a task complete.",
            "parameters": {
                "type": "object",
                "required": ["task_id"],
                "properties": {"task_id": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_task",
            "description": "Delete a task permanently.",
            "parameters": {
                "type": "object",
                "required": ["task_id"],
                "properties": {"task_id": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_reminder",
            "description": "Add a push notification reminder (Todoist Premium only). Free accounts get notified automatically via due times.",
            "parameters": {
                "type": "object",
                "required": ["task_id", "type"],
                "properties": {
                    "task_id":       {"type": "string"},
                    "type":          {"type": "string", "enum": ["relative", "absolute"]},
                    "minute_offset": {"type": "integer", "description": "Minutes before due (relative)"},
                    "due_datetime":  {"type": "string", "description": "ISO datetime e.g. '2026-06-22T19:00:00'"},
                },
            },
        },
    },
]

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM = """You are a Todoist assistant. Today is {today}.

Rules:
- Scheduling series (e.g. "30 videos over a month"): use create_tasks_bulk with a specific due_string per task. Skip weekends by default.
- Labels: snake_case — system_design, leetcode, x_posting, internship, personal_project.
- Priority: 1=normal, 2=medium, 3=high, 4=urgent.
- Push notifications come automatically when tasks have due times (Todoist app). add_reminder needs Premium.
- After bulk ops reply with a one-line summary: "Created 22 tasks, Jun 23 → Jul 24, weekdays at 7pm."
- Be concise. No fluff."""

# ---------------------------------------------------------------------------
# Core agent loop  — returns (updated_messages, reply_text)
# ---------------------------------------------------------------------------

def run(messages: list, log=print) -> tuple[list, str]:
    today = date.today().strftime("%B %d, %Y (%A)")

    # inject / refresh system message
    if messages and messages[0]["role"] == "system":
        messages[0]["content"] = SYSTEM.format(today=today)
    else:
        messages.insert(0, {"role": "system", "content": SYSTEM.format(today=today)})

    reply_text = ""

    while True:
        resp = client.chat.completions.create(
            model=MODEL,
            tools=TOOLS,
            messages=messages,
        )
        msg    = resp.choices[0].message
        reason = resp.choices[0].finish_reason
        messages.append(msg)

        if reason == "stop":
            reply_text = msg.content or ""
            break

        if reason == "tool_calls":
            tool_results = []
            for call in (msg.tool_calls or []):
                log(f"  [{call.function.name}] ", end="", flush=True)
                try:
                    args = json.loads(call.function.arguments)
                    out  = TOOL_FNS[call.function.name](args)
                    log("ok")
                    tool_results.append({
                        "role":         "tool",
                        "tool_call_id": call.id,
                        "content":      json.dumps(out),
                    })
                except Exception as e:
                    log(f"error: {e}")
                    tool_results.append({
                        "role":         "tool",
                        "tool_call_id": call.id,
                        "content":      f"Error: {e}",
                    })
            messages.extend(tool_results)

    return messages, reply_text

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    print("Todoist Agent  (DeepSeek via OpenRouter)")
    print("Commands: 'quit' to exit  |  'clear' to reset conversation")
    print("-" * 55)
    messages = []
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break
        if user_input.lower() == "clear":
            messages = []
            print("Conversation cleared.")
            continue
        messages.append({"role": "user", "content": user_input})
        messages, reply = run(messages)
        print(f"\nAssistant: {reply}")


if __name__ == "__main__":
    main()
