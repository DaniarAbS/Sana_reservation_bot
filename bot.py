# bot.py
# Telegram Room Reservation Bot
# Requirements:
# pip install python-telegram-bot==20.7 gspread oauth2client

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import os
import json
import logging
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ===================== CONFIG =====================
BOT_TOKEN = "8502506234:AAEc_6tJl5W3Kg8pZ3PQm2mnTc_595Lk2AY"
GOOGLE_CREDS_FILE = "credentials.json"
SHEET_NAME = "Sana_reservation_bot"  # Google Sheet name

# ===================== LOGGING =====================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ===================== GOOGLE SHEETS =====================
def get_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json", scope
    )
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    return sheet

sheet = get_sheet()

# ===================== STATES =====================
ROOM, MENTOR, DAY, TIME, THINGS, COMMENT = range(6)

# ===================== COMMANDS =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Sana Room Reservation Bot \n"
        "Commands:\n"
        "/reserve - create reservation\n"
        "/today - today reservations\n"
        "/day YYYY-MM-DD - reservations by day\n"
        "/delete ID - delete reservation"
    )

# ===================== RESERVATION FLOW =====================
async def reserve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter room name:")
    return ROOM

async def room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["room"] = update.message.text
    await update.message.reply_text("Enter mentor name:")
    return MENTOR

async def mentor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mentor"] = update.message.text
    await update.message.reply_text("Enter day (YYYY-MM-DD):")
    return DAY

async def day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["day"] = update.message.text
    await update.message.reply_text("Enter time (e.g. 10:00-11:00):")
    return TIME

async def time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["time"] = update.message.text
    await update.message.reply_text("Things to reserve (comma separated):")
    return THINGS

async def things(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["things"] = update.message.text
    await update.message.reply_text("Any comment?")
    return COMMENT

async def comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = context.user_data

    new_id = len(sheet.get_all_values()) + 1
    sheet.append_row([
        new_id,
        data["room"],
        data["mentor"],
        data["day"],
        data["time"],
        data["things"],
        update.message.text,
        user.username or user.first_name,
    ])

    await update.message.reply_text("✅ Reservation saved")
    return ConversationHandler.END

# ===================== SHOW TODAY =====================
async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today_str = datetime.now().strftime("%Y-%m-%d")
    rows = sheet.get_all_records()

    result = [
        f"ID {r['id']} | {r['room_name']} | {r['mentor_name']} | {r['time']} | {r['comment']}"
        for r in rows if r["day"].strip() == today_str
    ]

    if not result:
        await update.message.reply_text("No reservations today")
    else:
        await update.message.reply_text("\n".join(result))

# ===================== SHOW BY DAY =====================
async def by_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /day YYYY-MM-DD")
        return

    day_query = context.args[0]
    rows = sheet.get_all_records()

    result = [
        f"ID {r['id']} | {r['room_name']} | {r['mentor_name']} | {r['time']} | {r['comment']}"
        for r in rows if r["day"].strip() == day_query
    ]

    if not result:
        await update.message.reply_text("No reservations found")
    else:
        await update.message.reply_text("\n".join(result))

# ===================== DELETE =====================
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /delete ID")
        return

    del_id = int(context.args[0])
    cells = sheet.find(str(del_id))
    sheet.delete_rows(cells.row)

    await update.message.reply_text("❌ Reservation deleted")

# ===================== MAIN =====================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("reserve", reserve)],
        states={
            ROOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, room)],
            MENTOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, mentor)],
            DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, day)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, time)],
            THINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, things)],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, comment)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("day", by_day))
    app.add_handler(CommandHandler("delete", delete))

    app.run_polling()


if __name__ == "__main__":
    main()
