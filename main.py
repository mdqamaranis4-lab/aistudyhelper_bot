import telebot
from telebot import types
import google.generativeai as genai
import os
import time
from flask import Flask
from threading import Thread

# --- 1. LIVE SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online & Super Fast!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- 2. CONFIG ---
BOT_TOKEN = "8711731953:AAHnVNJrkYE-NcnbecMgklNZM7R01oheb4k"
GEMINI_API_KEY = "AIzaSyAmxeeA3QNYRK6megtfNRv1eFvG5HZmpwU"
ADMIN_ID = 8503782525 

bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

users = set() # Database link missing hone par ye temporary hai, ise restart pe clear hona bachein
user_states = {}

SYLLABUS = {
    "9": ["Number Systems", "Polynomials", "Lines and Angles", "Triangles", "Circles"],
    "10": ["Real Numbers", "Trigonometry", "Quadratic Equations", "Statistics"],
    "11": ["Sets", "Relations", "Limits", "Statistics"],
    "12": ["Matrices", "Integrals", "Vector Algebra", "3D Geometry"]
}

# --- 3. MENU ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.chat.id
    users.add(uid)
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    markup.add(
        types.InlineKeyboardButton("📖 Study (Syllabus & Chapters)", callback_data="study_main"),
        types.InlineKeyboardButton("🤖 AI Chat / Doubts", callback_data="state_ai"),
        types.InlineKeyboardButton("☎️ Contact Support", url="https://t.me/flaaxxx_run")
    )
    
    if uid == ADMIN_ID:
        markup.add(
            types.InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"),
            types.InlineKeyboardButton("📢 Broadcast (Image/Video/Text)", callback_data="admin_broadcast")
        )
    
    bot.send_message(uid, "🚀 **Bot Updated!**\nAb aap Broadcast mein Photos/Videos bhi bhej sakte hain.", reply_markup=markup, parse_mode="Markdown")

# --- 4. CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    cid = call.message.chat.id
    if call.data == "admin_broadcast":
        user_states[cid] = {"mode": "broadcast_active"}
        bot.send_message(cid, "📤 **Broadcast Mode ON:**\nAb koi bhi Message, Photo, ya Video bhejein, wo sabhi users ko chala jayega.")
    
    elif call.data == "study_main":
        markup = types.InlineKeyboardMarkup(row_width=2)
        for i in range(9, 13):
            markup.add(types.InlineKeyboardButton(f"Class {i}", callback_data=f"cls_{i}"))
        bot.edit_message_text("Apni Class select karein:", cid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("cls_"):
        cls = call.data.split("_")[1]
        user_states[cid] = {"class": cls}
        markup = types.InlineKeyboardMarkup(row_width=1)
        for ch in SYLLABUS.get(cls, []):
            markup.add(types.InlineKeyboardButton(ch, callback_data=f"ch_{ch}"))
        markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="study_main"))
        bot.edit_message_text(f"Class {cls} ke Chapters:", cid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("ch_"):
        chap = call.data.split("_")[1]
        bot.send_message(cid, f"⏳ {chap} ki details nikal raha hoon...")
        res = model.generate_content(f"Explain {chap} for Class {user_states[cid].get('class')} in Hinglish.")
        bot.send_message(cid, res.text)

# --- 5. BROADCAST & SEARCH LOGIC (FIXED) ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def handle_all(message):
    cid = message.chat.id
    state = user_states.get(cid, {})

    # 🔥 SMART BROADCAST (Text, Photo, Video Sab Jayega)
    if state.get("mode") == "broadcast_active" and cid == ADMIN_ID:
        count = 0
        for u in list(users):
            try:
                if message.content_type == 'text':
                    bot.send_message(u, message.text)
                elif message.content_type == 'photo':
                    bot.send_photo(u, message.photo[-1].file_id, caption=message.caption)
                elif message.content_type == 'video':
                    bot.send_video(u, message.video.file_id, caption=message.caption)
                count += 1
            except: pass
        bot.send_message(ADMIN_ID, f"✅ Broadcast Complete! {count} members ko mila.")
        user_states[cid] = {} # Mode reset
        return

    # 🤖 AI SEARCH
    if message.content_type == 'text' and not message.text.startswith('/'):
        bot.reply_to(message, "🔍 Searching...")
        try:
            res = model.generate_content(message.text)
            bot.reply_to(message, res.text)
        except: bot.reply_to(message, "❌ AI error! Thodi der baad try karein.")

    elif message.content_type == 'photo':
        bot.reply_to(message, "⏳ Solving Image...")
        file = bot.download_file(bot.get_file(message.photo[-1].file_id).file_path)
        res = model.generate_content([{"mime_type": "image/jpeg", "data": file}, "Solve this."])
        bot.reply_to(message, res.text)

if __name__ == "__main__":
    keep_alive()
    bot.polling(none_stop=True)
