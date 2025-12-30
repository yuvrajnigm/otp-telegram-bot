import re
import time
import os
import sys
import threading
import datetime
import requests
import phonenumbers
from phonenumbers import geocoder
from flask import Flask
from telegram import Bot
from telegram.ext import Application, CommandHandler

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")          # -1003406789899
ADMIN_ID = 8449115253

CR_API_1_URL = "http://51.77.216.195/crapi/dgroup/viewstats"
CR_API_2_URL = "http://147.135.212.197/crapi/had/viewstats"

CR_API_1_TOKEN = os.getenv("CR_API_1_TOKEN")
CR_API_2_TOKEN = os.getenv("CR_API_2_TOKEN")

NUMBER_CHANNEL = "https://t.me/YUVRAJNUMBERS"

SERVICE_EMOJI = {
    "WHATSAPP": "🟢",
    "GOOGLE": "🔵",
    "TELEGRAM": "✈️",
    "FACEBOOK": "🔷",
    "INSTAGRAM": "📸",
    "TWITTER": "🐦",
    "MICROSOFT": "🪟",
    "UNKNOWN": "❔"
}

# ================= INIT =================

bot = Bot(token=BOT_TOKEN)
app = Flask(__name__)

SEEN_OTPS = set()
BOT_START_TIME = time.time()
TOTAL_OTPS = 0

# ================= HELPERS =================

def admin_log(text):
    try:
        bot.send_message(chat_id=ADMIN_ID, text=f"🛠 BOT LOG:\n{text}")
    except:
        pass

def detect_otp(message):
    m = re.search(r'\b\d{3}[- ]?\d{3}\b|\b\d{4,6}\b', message)
    return m.group().replace("-", "") if m else "N/A"

def detect_service(message):
    m = message.lower()
    if "whatsapp" in m:
        return "WHATSAPP"
    if "google" in m:
        return "GOOGLE"
    if "telegram" in m:
        return "TELEGRAM"
    if "facebook" in m or "meta" in m:
        return "FACEBOOK"
    return "UNKNOWN"

def mask_number(num):
    if len(num) < 7:
        return num
    return num[:6] + "**" + num[-3:]

def detect_country(number):
    try:
        p = phonenumbers.parse("+" + number)
        country = geocoder.description_for_number(p, "en")
        region = phonenumbers.region_code_for_number(p)
        flag = "".join(chr(127397 + ord(c)) for c in region)
        return country, flag
    except:
        return "Unknown", "🌍"

# ================= CR API =================

def fetch_from_cr_api(url, token):
    try:
        r = requests.get(url, params={
            "token": token,
            "records": 10
        }, timeout=10)
        j = r.json()
        if j.get("status") != "success":
            return []
        return j.get("data", [])
    except Exception as e:
        admin_log(f"API fetch error: {e}")
        return []

def process_api_data(rows):
    global TOTAL_OTPS

    for row in rows:
        try:
            number = row.get("num", "")
            message = row.get("message", "")
            uid = f"{number}-{message}"

            if uid in SEEN_OTPS:
                continue
            SEEN_OTPS.add(uid)

            otp = detect_otp(message)
            service = detect_service(message)
            service_icon = SERVICE_EMOJI.get(service, "❔")
            country, flag = detect_country(number)

            masked = mask_number(number)
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            text = f"""
✅ {service_icon} {flag} {country} | {service} OTP Received

━━━━━━━━━━━━━━━
📱 Number: {masked}
🔑 OTP Code: {otp}
🛠 Service: {service}
🌍 Country: {flag} {country}
⏰ Time: {now}
━━━━━━━━━━━━━━━

💬 Message:
{message}

📢 Numbers Channel:
{NUMBER_CHANNEL}
"""

            bot.send_message(chat_id=CHAT_ID, text=text)
            TOTAL_OTPS += 1

        except Exception as e:
            admin_log(f"Processing error: {e}")

# ================= LOOP =================

def auto_fetch_loop():
    while True:
        try:
            d1 = fetch_from_cr_api(CR_API_1_URL, CR_API_1_TOKEN)
            d2 = fetch_from_cr_api(CR_API_2_URL, CR_API_2_TOKEN)
            process_api_data(d1)
            process_api_data(d2)
        except Exception as e:
            admin_log(f"Loop error: {e}")
        time.sleep(15)

threading.Thread(target=auto_fetch_loop, daemon=True).start()

# ================= ADMIN COMMANDS =================

async def status_cmd(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    uptime = int(time.time() - BOT_START_TIME)
    h = uptime // 3600
    m = (uptime % 3600) // 60

    await update.message.reply_text(
        f"📊 BOT STATUS\n\n"
        f"✅ Status: ONLINE\n"
        f"⏱ Uptime: {h}h {m}m\n"
        f"📨 OTP Sent: {TOTAL_OTPS}\n"
        f"🌍 Country Detect: ENABLED\n"
        f"🔁 Duplicate Block: ENABLED\n"
        f"⚠️ Error Mode: SILENT"
    )

async def restart_cmd(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("♻️ Restarting bot…")
    admin_log("Restart triggered")
    os._exit(0)

def run_commands():
    app_bot = Application.builder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("status", status_cmd))
    app_bot.add_handler(CommandHandler("restart", restart_cmd))
    app_bot.run_polling()

threading.Thread(target=run_commands, daemon=True).start()

# ================= KEEP ALIVE =================

@app.route("/")
def home():
    return "OTP Bot Running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
