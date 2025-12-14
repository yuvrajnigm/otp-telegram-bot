# -*- coding: utf-8 -*-
import asyncio, re, os, json, threading, traceback
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
# ==============================================


# ================= KEEP ALIVE ==================
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot Alive"

def run_flask():
    app_flask.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_flask, daemon=True).start()
# ==============================================


def load_state():
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w") as f:
            json.dump({}, f)
    return json.load(open(STATE_FILE))


def save_state(data):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def extract_otp(text):
    m = re.search(r"\b\d{4,8}\b|\d{3}-\d{3}", text)
    return m.group(0) if m else "N/A"


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


# ================= IVASMS ======================
async def fetch_ivasms(client):
    login = "https://www.ivasms.com/login"
    panel = "https://www.ivasms.com/portal/sms/received"

    r = await client.get(login)
    soup = BeautifulSoup(r.text, "html.parser")
    token = soup.find("input", {"name": "_token"})["value"]

    await client.post(
        login,
        data={
            "email": IVASMS_USER,
            "password": IVASMS_PASS,
            "_token": token,
        },
    )

    page = await client.get(panel)
    return page.text


# ================= 185 =========================
async def fetch_185(client):
    await client.post(
        "http://185.2.83.39/ints/login",
        data={"username": INTS_USER, "password": INTS_PASS},
    )
    r = await client.get("http://185.2.83.39/ints/agent/SMSCDRStats")
    return r.text


# ================= WORKER ======================
async def check_otps(context: ContextTypes.DEFAULT_TYPE):
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
                        await context.bot.send_message(
                            chat_id=GROUP_ID,
                            text=text,
                            parse_mode="HTML",
                        )
                        await context.bot.send_message(
                            chat_id=OTP_CHANNEL,
                            text=text,
                            parse_mode="HTML",
                        )
                    except Exception as e:
                        print("TELEGRAM SEND ERROR:", e)

            except Exception as e:
                print(f"{name} ERROR:", e)
                traceback.print_exc()

    save_state(state)


# ================= BOT START ===================
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.effective_user.id) in ADMIN_IDS:
            await update.message.reply_text("✅ OTP Bot Running")

    application.add_handler(CommandHandler("start", start))
    application.job_queue.run_repeating(check_otps, interval=POLL_INTERVAL, first=5)

    print("🚀 OTP BOT STARTED")
    application.run_polling()


if __name__ == "__main__":
    main()
            await update.message.reply_text("✅ OTP Bot Running")

    app.add_handler(CommandHandler("start", start))
    app.job_queue.run_repeating(check_otps, interval=POLL_INTERVAL, first=5)

    print("🚀 OTP BOT STARTED")
    app.run_polling()

if __name__ == "__main__":
    main()
