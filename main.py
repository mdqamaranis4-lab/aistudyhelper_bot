import telebot
from telebot import types
import google.generativeai as genai
import os
import time
from flask import Flask
from threading import Thread

# --- 1. SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

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

users = set()
user_states = {}

SYLLABUS = {
    "9": ["Number Systems", "Polynomials", "Lines and Angles", "Triangles", "Quadrilaterals", "Circles", "Heron's Formula", "Surface Areas"],
    "10": ["Real Numbers", "Polynomials", "Quadratic Equations", "Trigonometry", "Circles", "Statistics", "Probability"],
    "11": ["Sets", "Trigonometry", "Permutations", "Limits", "Probability"],
    "12": ["Matrices", "Determinants", "Integrals", "Differential Equations", "Vector Algebra"]
}

# --- 3. START COMMAND ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.chat.id
    users.add(uid)
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    markup.add(
        types.InlineKeyboardButton("📖 Study (Syllabus & Chapters)", callback_data="study_main"),
        types.InlineKeyboardButton("📄 Photo to Text", callback_data="state_ocr"),
        types.InlineKeyboardButton("🔍 Scan and Search", callback_data="state_scan"),
        types.InlineKeyboardButton("🤖 AI Chat / Doubts", callback_data="state_ai"),
        types.InlineKeyboardButton("☎️ Contact Support (@flaaxxx_run)", url="https://t.me/flaaxxx_run")
    )
    
    if uid == ADMIN_ID:
        markup.add(
            types.InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"),
            types.InlineKeyboardButton("📢 Send Broadcast (Media Support)", callback_data="admin_broadcast")
        )
    
    bot.send_message(uid, f"✨ **All Buttons Restored!**\nAapka ID: `{uid}`", reply_markup=markup, parse_mode="Markdown")

# --- 4. CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    cid = call.message.chat.id
    bot.answer_callback_query(call.id)

    if call.data == "study_main":
        markup = types.InlineKeyboardMarkup(row_width=2)
        for i in range(9, 13):
            markup.add(types.InlineKeyboardButton(f"Class {i}", callback_data=f"cls_{i}"))
        markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="back_home"))
        bot.edit_message_text("Apni Class chunein:", cid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("cls_"):
        cls = call.data.split("_")[1]
        user_states[cid] = {"class": cls}
        markup = types.InlineKeyboardMarkup(row_width=1)
        for ch in SYLLABUS.get(cls, []):
            markup.add(types.InlineKeyboardButton(ch, callback_data=f"ch_{ch}"))
        markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="study_main"))
        bot.edit_message_text(f"Class {cls} Chapters:", cid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("ch_"):
        chap = call.data.split("_")[1]
        cls = user_states[cid].get("class", "10")
        bot.send_message(cid, f"⏳ Generating solution for **{chap}** (Class {cls})...", parse_mode="Markdown")
        try:
            res = model.generate_content(f"Provide a clear summary and 5 important questions for Class {cls} {chap} in Hinglish.")
            bot.send_message(cid, res.text)
        except: bot.send_message(cid, "❌ AI is busy. Try again.")

    elif call.data == "admin_broadcast":
        user_states[cid] = {"mode": "broadcast_mode"}
        bot.send_message(cid, "📤 **Broadcast Active:**\nAb koi bhi Text, Photo ya Video bhejein, wo sabko jayega.")

    elif call.data == "admin_panel":
        bot.send_message(cid, f"📊 **Bot Stats**\nTotal Users: {len(users)}\nAPI: Active ✅")

    elif call.data == "back_home":
        start_cmd(call.message)

    elif call.data.startswith("state_"):
        user_states[cid] = {"mode": call.data.split("_")[1]}
        bot.send_message(cid, "✅ Mode Set! Send your question/photo.")

# --- 5. MEDIA & AI HANDLER ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def handle_all(message):
    cid = message.chat.id
    state = user_states.get(cid, {})

    # 🔥 Broadcast Logic
    if state.get("mode") == "broadcast_mode" and cid == ADMIN_ID:
        count = 0
        for u in list(users):
            try:
                if message.content_type == 'text': bot.send_message(u, message.text)
                elif message.content_type == 'photo': bot.send_photo(u, message.photo[-1].file_id, caption=message.caption)
                elif message.content_type == 'video': bot.send_video(u, message.video.file_id, caption=message.caption)
                count += 1
            except: pass
        bot.send_message(ADMIN_ID, f"✅ Done! Sent to {count} users.")
        user_states[cid] = {}
        return

    # 🤖 AI Search
    if message.content_type == 'text' and not message.text.startswith('/'):
        bot.reply_to(message, "🔍 Searching...")
        try:
            res = model.generate_content(message.text)
            bot.reply_to(message, res.text)
        except: bot.reply_to(message, "❌ AI error!")

    elif message.content_type == 'photo':
        bot.reply_to(message, "⏳ Reading Image...")
        try:
            file = bot.download_file(bot.get_file(message.photo[-1].file_id).file_path)
            res = model.generate_content([{"mime_type": "image/jpeg", "data": file}, "Solve this in Hinglish."])
            bot.reply_to(message, res.text)
        except: bot.reply_to(message, "❌ Photo processing error!")

if __name__ == "__main__":
    keep_alive()
    bot.polling(none_stop=True)
