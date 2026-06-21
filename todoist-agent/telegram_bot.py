#!/usr/bin/env python3
"""Telegram bot frontend for the Todoist agent. Run: python telegram_bot.py"""

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from agent import run

load_dotenv()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise SystemExit("Missing TELEGRAM_BOT_TOKEN — get one from @BotFather and add to .env")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.WARNING,
)

# Per-chat conversation history  {chat_id: [messages]}
conversations: dict[str, list] = {}

HELP_TEXT = (
    "Todoist Agent — I manage your tasks via natural language.\n\n"
    "Examples:\n"
    "• Schedule 30 system design videos in July, weekdays at 7pm\n"
    "• Add daily leetcode at 9am for the next 2 weeks, high priority\n"
    "• What's due today?\n"
    "• Reschedule all system\\_design tasks to 8pm\n"
    "• Delete all overdue tasks\n\n"
    "/clear — reset this conversation\n"
    "/help — show this message"
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    conversations[chat_id] = []
    await update.message.reply_text("Conversation cleared.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    text    = update.message.text.strip()

    if chat_id not in conversations:
        conversations[chat_id] = []

    # send typing indicator + placeholder so user sees activity
    await update.message.chat.send_action("typing")
    status_msg = await update.message.reply_text("Working on it...")

    conversations[chat_id].append({"role": "user", "content": text})

    try:
        # suppress stdout prints from tool calls — they still log server-side
        conversations[chat_id], reply = run(
            conversations[chat_id],
            log=lambda *a, **kw: print(*a, **kw),   # keeps server logs
        )
        await status_msg.edit_text(reply or "Done.")
    except Exception as e:
        conversations[chat_id].pop()   # remove failed user message so user can retry
        await status_msg.edit_text(f"Error: {e}")


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Telegram bot running — press Ctrl+C to stop")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
