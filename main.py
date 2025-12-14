# -*- coding: utf-8 -*-
# Importing necessary libraries
import asyncio
import re
import httpx
from bs4 import BeautifulSoup
import time
import json
import os
import traceback
from urllib.parse import urljoin
from datetime import datetime, timedelta
# New library added
# Import 'Defaults' from telegram.ext for the latest JobQueue configuration
# 'JobQueue' class import is required for manual initialization
from telegram.ext import Application, CommandHandler, ContextTypes, Defaults, JobQueue 
from telegram import Update
from telegram.constants import ParseMode # For robust MarkdownV2 parsing

# --- Configuration (Fill in your details) ---
# Your Telegram Bot Token here. You can get it from BotFather.
# Example: YOUR_BOT_TOKEN = "1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
YOUR_BOT_TOKEN = "8568220927:AAFwKIUpgDhXPJPBzWn7c5dCU9EAtdx0PQY" 

# ==================== New Addition: Multiple Admin IDs ====================
# Add your and other admins' Telegram User IDs to the list below
ADMIN_CHAT_IDS = ["8221767181"] 
# =================================================================

# Old chat IDs kept for the first run
INITIAL_CHAT_IDS = ["-1003406789899"] 

LOGIN_URL = "https://www.ivasms.com/login"
BASE_URL = "https://www.ivasms.com/"
SMS_API_ENDPOINT = "https://www.ivasms.com/portal/sms/received/getsms"

USERNAME = "tgonly712@gmail.com"
PASSWORD = "Yuvraj2008"

# Reduced interval to 2 seconds to keep the bot responsive and reduce server load
POLLING_INTERVAL_SECONDS = 2 

# ... (Rest of the config and helper functions remain unchanged) ...
# (Lines 76 - 431)

# --- Core Functions ---
def escape_markdown(text):
    # Escapes markdown special characters for MarkdownV2 formatting
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

def load_processed_ids():
    if not os.path.exists(STATE_FILE): return set()
    try:
        with open(STATE_FILE, 'r') as f: return set(json.load(f))
    except (json.JSONDecodeError, FileNotFoundError): return set()

def save_processed_id(sms_id):
    processed_ids = load_processed_ids()
    processed_ids.add(sms_id)
    with open(STATE_FILE, 'w') as f: json.dump(list(processed_ids), f)

# ... (fetch_sms_from_api function remains unchanged) ...

async def send_telegram_message(context: ContextTypes.DEFAULT_TYPE, chat_id: str, message_data: dict):
    try:
        time_str, number_str = message_data.get("time", "N/A"), message_data.get("number", "N/A")
        country_name, flag_emoji = message_data.get("country", "N/A"), message_data.get("flag", "🏴‍☠️")
        service_name, code_str = message_data.get("service", "N/A"), message_data.get("code", "N/A")
        full_sms_text = message_data.get("full_sms", "N/A")
        
        # Add service emoji
        service_emoji = SERVICE_EMOJIS.get(service_name, "❓")

        full_message = (f"🔔 *You have successfully received OTP*\n\n" 
                        f"📞 *Number:* `{escape_markdown(number_str)}`\n" 
                        f"🔑 *Code:* `{escape_markdown(code_str)}`\n" 
                        f"🏆 *Service:* {service_emoji} {escape_markdown(service_name)}\n" 
                        f"🌎 *Country:* {escape_markdown(country_name)} {flag_emoji}\n" 
                        f"⏳ *Time:* `{escape_markdown(time_str)}`\n\n" 
                        f"💬 *Message:*\n" 
                        f"```\n{escape_markdown(full_sms_text)}\n```")
        
        # Using ParseMode.MARKDOWN_V2 for better compatibility
        await context.bot.send_message(chat_id=chat_id, text=full_message, parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e:
        print(f"❌ Error sending message to chat ID {chat_id}: {e}")
        try:
             await context.bot.send_message(chat_id=chat_id, text=f"🔔 New OTP from {number_str} ({country_name}):\nCode: {code_str}\nMessage: {full_sms_text}", parse_mode=None)
        except Exception as e2:
             print(f"❌ Critical error sending message: {e2}")

# ... (check_sms_job function remains unchanged) ...

# --- Main part to start the bot ---
def main():
    print("🚀 iVasms to Telegram Bot is starting...")

    if not ADMIN_CHAT_IDS:
        print("\n!!! 🔴 WARNING: You have not correctly set admin IDs in your ADMIN_CHAT_IDS list. !!!\n")
        return

    # FIX 1: Removed 'allow_sending_messages_during_build' parameter
    # Create the Defaults object without any arguments
    defaults = Defaults()
    
    # FIX 2: Manually create the JobQueue and add it to the Application builder
    job_queue_instance = JobQueue()
    
    # Build the Application using the Defaults object and the JobQueue instance
    application = (Application.builder()
                   .token(YOUR_BOT_TOKEN)
                   .defaults(defaults)
                   .job_queue(job_queue_instance) # Add job queue instance
                   .build())

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("add_chat", add_chat_command))
    application.add_handler(CommandHandler("remove_chat", remove_chat_command))
    application.add_handler(CommandHandler("list_chats", list_chats_command))

    # Set the main job to run repeatedly at a specific interval
    job_queue = application.job_queue
    
    # Safety check to ensure Job Queue was correctly initialized
    if job_queue:
        job_queue.run_repeating(check_sms_job, interval=POLLING_INTERVAL_SECONDS, first=1)
    else:
        print("❌ CRITICAL: Job Queue failed to initialize. Cannot start SMS checking job.")
        return

    print(f"🚀 Checking for new messages every {POLLING_INTERVAL_SECONDS} seconds.")
    print("🤖 Bot is now online. Ready to listen for commands.")
    print("⚠️ Press Ctrl+C to stop the bot.")
    
    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
