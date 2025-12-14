
# -*- coding: utf-8 -*-

import os
import re
import json
import asyncio
import threading
import traceback
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from flask import Flask

from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update


# ================= BASIC CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = ["8221767181", "8449115253"]

GROUP_ID = -1003406789899
OTP_CHANNEL = "@YUVRAJNUMERSOTP"

IVASMS_USER = os.getenv("IVASMS_USER")
IVASMS_PASS = os.getenv("IVASMS_PASS")

INTS_USER = os.getenv("INTS_USER")
INTS_PASS = os.getenv("INTS_PASS")

STATE_FILE = "processed_sms_ids.json"
POLL_INTERVAL = 3
# ===============================================


# ================= KEEP ALIVE ===================
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot Alive"

def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_flask, daemon=True).start()
# ===============================================


def load_state():
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w") as f:
            json.dump({}, f)
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(data):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def extract_otp(text):
    m = re.search(r"\b\d{4,8}\b|\d{3}-\d{3}", text)
    return m.group(0) if m else "N/A"

def mask_number(text):
    # number extract (10–14 digit, + optional)
    m = re.search(r"\+?\d{10,14}", text)
    if not m:
        return "Unknown"

    num = m.group(0)

    if len(num) <= 6:
        return num

    return num[:3] + "****" + num[-3:]

def premium_message(source, otp, raw):
    clean_msg = re.sub("<.*?>", "", raw)[:1000]
    return (
        f"🔔 <b>New OTP Received</b>\n\n"
        f"🏷 <b>Source:</b> {source}\n"
        f"🔑 <b>OTP:</b> <code>{otp}</code>\n"
        f"⏰ <b>Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
        f"💬 <b>Message:</b>\n{clean_msg}\n\n"
        f"⚡ Powered by YUVRAJ"
    )


# ================= IVASMS =======================
async def fetch_ivasms(client):
    login_url = "https://www.ivasms.com/login"
    panel_url = "panel_url = "https://www.ivasms.com/portal/live/my_sms"

    r = await client.get(login_url)

    token = None
    soup = BeautifulSoup(r.text, "html.parser")
    token_tag = soup.find("input", {"name": "_token"})
    if token_tag:
        token = token_tag.get("value")

    payload = {
        "email": IVASMS_USER,
        "password": IVASMS_PASS
    }

    if token:
        payload["_token"] = token

    await client.post(login_url, data=payload)

    page = await client.get(panel_url)
    return page.text


# ================= 185 ==========================
async def fetch_185(client):
    await client.post(
        "http://185.2.83.39/ints/login",
        data={
            "username": INTS_USER,
            "password": INTS_PASS
        }
    )
    r = await client.get("http://185.2.83.39/ints/agent/SMSCDRStats")
    return r.text


# ================= OTP CHECK ====================
async def check_otps(application: Application):
    state = load_state()

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for name, func in [("IVASMS", fetch_ivasms), ("INTS-185", fetch_185)]:
            try:
                html = await func(client)
                matches = re.findall(r".{0,40}\b\d{4,8}\b.{0,40}", html)

                for msg in matches:
                    otp = extract_otp(msg)
                    key = f"{name}-{otp}"

                    if state.get(key) == msg:
                        continue

                    state[key] = msg
                    text = premium_message(name, otp, msg)

                    try:
                        await application.bot.send_message(
                            chat_id=GROUP_ID,
                            text=text,
                            parse_mode="HTML"
                        )
                        await application.bot.send_message(
                            chat_id=OTP_CHANNEL,
                            text=text,
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        print("TELEGRAM SEND ERROR:", e)

            except Exception as e:
                print(f"{name} ERROR:", e)
                traceback.print_exc()

    save_state(state)


# ================= BACKGROUND LOOP ==============
async def otp_loop(application: Application):
    await asyncio.sleep(5)
    while True:
        await check_otps(application)
        await asyncio.sleep(POLL_INTERVAL)


# ================= BOT START ====================
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.effective_user.id) in ADMIN_IDS:
            await update.message.reply_text("✅ OTP Bot Running")

    application.add_handler(CommandHandler("start", start))

    async def post_init(app):
        asyncio.create_task(otp_loop(app))

    application.post_init = post_init

    print("🚀 OTP BOT STARTED")
    application.run_polling()


if __name__ == "__main__":
    main()
