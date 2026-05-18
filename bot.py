import requests
import json
import time
import os
import sqlite3
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer

# =========================================
# CONFIGURATION (Aapki Settings)
# =========================================
BOT_TOKEN = "8890676774:AAHOBKoCY--8J2HETlhBhDkxJeAFBvlal4Y"  # UPI Giveaway Bot Token
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Mandatory Join Settings
MANDATORY_CHANNEL = "@nobitaosint"
MANDATORY_BOT = "Nobita_infoo_bot"

REFERRAL_BONUS = 10.0
DAILY_BONUS_AMOUNT = 10.0
MIN_WITHDRAWAL = 100.0  # Minimum withdrawal ₹100 set kar diya hai
DB_FILE = "giveaway_database.db"

# Aapka naya wala mast logo banner link
BANNER_URL = "https://raw.githubusercontent.com/Bikash7311/upi-giveway22/main/17790986288435596287189569091555_8c74f4.jpg"

user_states = {}

# =========================================
# DATABASE CODE
# =========================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY, 
                        balance REAL DEFAULT 0.0, 
                        last_bonus_time INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS referrals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        referrer_id INTEGER,
                        referred_id INTEGER UNIQUE)''')
    conn.commit()
    conn.close()

def get_user_data(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, last_bonus_time FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if not res:
        cursor.execute("INSERT INTO users (user_id, balance, last_bonus_time) VALUES (?, 0.0, 0)", (user_id,))
        conn.commit()
        res = (0.0, 0)
    conn.close()
    return res

def update_balance(user_id, amount):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def update_bonus_time(user_id, current_time):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_bonus_time = ? WHERE user_id = ?", (current_time, user_id))
    conn.commit()
    conn.close()

def add_referral(referrer_id, referred_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, referred_id))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def get_referral_count(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

# =========================================
# TELEGRAM SYSTEM LOGIC
# =========================================
def is_user_joined(user_id):
    try:
        url = API_URL + "/getChatMember"
        params = {"chat_id": MANDATORY_CHANNEL, "user_id": user_id}
        response = requests.get(url, params=params, timeout=10).json()
        if response.get("ok") and response["result"]["status"] in ["member", "administrator", "creator"]:
            return True
        return False
    except: return False

def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    url = API_URL + "/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup: payload["reply_markup"] = json.dumps(reply_markup)
    if parse_mode: payload["parse_mode"] = parse_mode
    try: requests.post(url, data=payload, timeout=10)
    except: pass

def send_photo(chat_id, photo_url, caption, reply_markup=None, parse_mode=None):
    url = API_URL + "/sendPhoto"
    payload = {"chat_id": chat_id, "photo": photo_url, "caption": caption}
    if reply_markup: payload["reply_markup"] = json.dumps(reply_markup)
    if parse_mode: payload["parse_mode"] = parse_mode
    try: requests.post(url, data=payload, timeout=10)
    except: pass

def answer_callback_query(callback_query_id, text):
    url = API_URL + "/answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id, "text": text}
    try: requests.post(url, data=payload, timeout=10)
    except: pass

def get_join_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "📢 Join Channel", "url": f"https://t.me/{MANDATORY_CHANNEL.replace('@','')}"}],
            [{"text": "🤖 Start Partner Bot", "url": f"https://t.me/{MANDATORY_BOT}"}],
            [{"text": "✅ Check Mandatory Join", "callback_data": "verify_join"}]
        ]
    }

def get_mainframe_menu():
    return {
        "inline_keyboard": [
            [{"text": "💰 My Balance", "callback_data": "menu_balance"}, {"text": "🎁 Daily Bonus", "callback_data": "menu_bonus"}],
            [{"text": "👥 Referral Link", "callback_data": "menu_referral"}, {"text": "💳 Withdrawal", "callback_data": "menu_withdraw"}]
        ]
    }

def get_back_keyboard():
    return {"inline_keyboard": [[{"text": "🔙 Back To Menu", "callback_data": "go_back"}]]}

def handle_message(message):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    user_text = message.get("text", "").strip()

    if not is_user_joined(user_id):
        join_msg = (
            "👋 <b>Welcome to UPI Giveaway Bot!</b>\n\n"
            "Bot use karne ke liye ye dono tasks complete karna mandatory hai:\n\n"
            f"1️⃣ Hamara channel {MANDATORY_CHANNEL} join karein.\n"
            f"2️⃣ Hamare partner bot @{MANDATORY_BOT} ko start karein.\n\n"
            "👇 Dono karne ke baad niche check button par click karein."
        )
        send_message(chat_id, join_msg, reply_markup=get_join_keyboard(), parse_mode="HTML")
        return

    get_user_data(user_id)

    if user_text.startswith("/start"):
        parts = user_text.split(" ")
        if len(parts) > 1:
            try:
                referrer_id = int(parts[1])
                if referrer_id != user_id:
                    if add_referral(referrer_id, user_id):
                        update_balance(referrer_id, REFERRAL_BONUS)
                        send_message(referrer_id, f"🎉 <b>New Referral!</b>\n\n💸 <b>+₹
