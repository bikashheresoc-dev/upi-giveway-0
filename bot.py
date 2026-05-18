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
BOT_TOKEN = "8890676774:AAHOBKoCY--8J2HETlhBhDkxJeAFBvlal4Y"  
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Mandatory Join Settings
MANDATORY_CHANNEL = "@nobitaosint"
MANDATORY_BOT = "Nobita_infoo_bot"

REFERRAL_BONUS = 10.0
DAILY_BONUS_AMOUNT = 10.0
MIN_WITHDRAWAL = 50.0  
DB_FILE = "giveaway_database.db"

# 100% WORKING IMAGE LINK (Aapka Logo Banner)
BANNER_URL = "https://raw.githubusercontent.com/Bikash7311/upi-giveway22/main/file_00000000699c72078bf5815b0d1a0995.png"

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
    try: 
        res = requests.post(url, data=payload, timeout=10).json()
        # Backup plan: Agar GitHub image load nahi hui, toh normal text message bhej dega taaki bot crash na ho
        if not res.get("ok"):
            send_message(chat_id, caption, reply_markup=reply_markup, parse_mode=parse_mode)
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

# AAPKE 4 MAST OPTIONS NEECHE WALE
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
                        send_message(referrer_id, f"🎉 <b>New Referral!</b>\n\n💸 <b>+₹{int(REFERRAL_BONUS)} Added</b> to your balance!")
            except: pass

        welcome_text = (
            f"🎁 <b>WELCOME TO UPI GIVEAWAY MAINFRAME</b> 🎁\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Per Referral: <b>₹{int(REFERRAL_BONUS)}</b>\n"
            f"🎁 Daily Bonus: <b>₹{int(DAILY_BONUS_AMOUNT)}</b>\n"
            f"💳 Minimum Payout: <b>₹{int(MIN_WITHDRAWAL)}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Niche diye gaye buttons se apna wallet manage karein 👇"
        )
        send_photo(chat_id, BANNER_URL, welcome_text, reply_markup=get_mainframe_menu(), parse_mode="HTML")
        user_states[chat_id] = "idle"
        return

    if user_states.get(chat_id) == "awaiting_upi":
        if "@" in user_text and len(user_text) > 5:
            balance, _ = get_user_data(user_id)
            if balance >= MIN_WITHDRAWAL:
                update_balance(user_id, -balance)
                success_msg = (
                    f"🎉 <b>CONGRATULATIONS !!!</b> 🎉\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"✅ Aapki withdrawal request successfully lag chuki hai!\n\n"
                    f"💰 <b>Amount:</b> ₹{balance}\n"
                    f"💳 <b>UPI ID:</b> <code>{user_text}</code>\n"
                    f"⏳ <b>Status:</b> Pending (Verification checking)\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📢 <i>Kripya <b>1-2 hours</b> tak wait karein. Admin aapki details verify karke direct aapke account me paise bhej dega! Thank you.</i>"
                )
                send_message(chat_id, success_msg, reply_markup=get_back_keyboard(), parse_mode="HTML")
            user_states[chat_id] = "idle"
        else:
            send_message(chat_id, "❌ <b>Galat UPI ID!</b> Kripya sahi UPI ID bhejiye:")
        return

def handle_callback(callback):
    callback_id = callback["id"]
    chat_id = callback["message"]["chat"]["id"]
    user_id = callback["from"]["id"]
    data = callback["data"]

    if data == "verify_join":
        if is_user_joined(user_id):
            answer_callback_query(callback_id, "✅ Pass!")
            welcome_text = f"🎁 <b>WELCOME TO UPI GIVEAWAY MAINFRAME</b> 🎁\n\nNiche diye gaye buttons se apna wallet manage karein 👇"
            send_photo(chat_id, BANNER_URL, welcome_text, reply_markup=get_mainframe_menu(), parse_mode="HTML")
        else:
            answer_callback_query(callback_id, "❌ Join pending!")
        return

    if not is_user_joined(user_id): return

    balance, last_bonus = get_user_data(user_id)

    if data == "menu_balance":
        bal_text = (
            f"💳 <b>YOUR WALLET BALANCE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Current Balance:</b> <code>₹{balance}</code>\n"
            f"👥 <b>Total Referrals:</b> <code>{get_referral_count(user_id)} Friends</code>\n\n"
            f"📢 <i>Note: Per Referral ₹10 milte hain.</i>"
        )
        send_message(chat_id, bal_text, reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif data == "menu_referral":
        ref_link = f"https://t.me/Upi_givewaybot?start={user_id}"
        ref_text = (
            f"👥 <b>REFERRAL PROGRAM PANEL</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 <b>Per Referral Reward:</b> ₹{int(REFERRAL_BONUS)}\n\n"
            f"🔗 <b>Aapka Personal Link:</b>\n<code>{ref_link}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        send_message(chat_id, ref_text, reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif data == "menu_bonus":
        now = int(time.time())
        if now - last_bonus >= 86400:
            update_balance(user_id, DAILY_BONUS_AMOUNT)
            update_bonus_time(user_id, now)
            send_message(chat_id, f"🎁 <b>Daily Bonus Claimed! +₹10 Added</b>\n\n🔄 Agla bonus 24 hours baad milega!", reply_markup=get_back_keyboard(), parse_mode="HTML")
        else:
            send_message(chat_id, f"⏳ Aap bonus claim kar chuke hain! Kripya agle bonus ke liye 24 ghante ka intezar karein.", reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif data == "menu_withdraw":
        if balance < MIN_WITHDRAWAL:
            answer_callback_query(callback_id, "❌ Minimum Withdrawal ₹50")
            lock_text = (
                f"📊 <b>REFERRAL TARGET STATUS</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Paise nikalne ke liye target poora karein:\n\n"
                f"👥 5 Referrals  = <b>₹50</b> (Min withdrawal)\n"
                f"👥 10 Referrals = <b>₹100</b>\n"
                f"👥 20 Referrals = <b>₹200</b>\n"
                f"👥 50 Referrals = <b>₹500</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ Aapka current balance: <b>₹{balance}</b>\n"
                f"🛑 <b>Minimum withdrawal ₹{int(MIN_WITHDRAWAL)} rs hai!</b>\n\n"
                f"💡 Dosto ko invite karke target poora karein!"
            )
            send_message(chat_id, lock_text, reply_markup=get_back_keyboard(), parse_mode="HTML")
        else:
            answer_callback_query(callback_id, "💳 Withdrawal Active")
            send_message(chat_id, "💸 <b>WITHDRAWAL PROTOCOL ACTIVE</b>\n\nKripya apni active <b>UPI ID</b> niche type karke send karein:")
            user_states[chat_id] = "awaiting_upi"

    elif data == "go_back":
        welcome_text = f"🎁 <b>WELCOME TO UPI GIVEAWAY MAINFRAME</b> 🎁\n\nNiche diye gaye buttons se apna wallet manage karein 👇"
        send_photo(chat_id, BANNER_URL, welcome_text, reply_markup=get_mainframe_menu(), parse_mode="HTML")

class WebServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ONLINE")

def bot_polling():
    offset = 0
    while True:
        try:
            response = requests.get(API_URL + "/getUpdates", params={"timeout": 30, "offset": offset}, timeout=35).json()
            if response.get("ok"):
                for update in response["result"]:
                    offset = update["update_id"] + 1
                    if "message" in update: handle_message(update["message"])
                    elif "callback_query" in update: handle_callback(update["callback_query"])
        except: time.sleep(1)

if __name__ == "__main__":
    init_db()
    Thread(target=lambda: HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 8080))), WebServer).serve_forever(), daemon=True).start()
    bot_polling()
