import telebot
from telebot import types
import google.generativeai as genai
import os
import time
from flask import Flask
from threading import Thread

# --- 1. RENDER LIVE SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Running Fast!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- 2. CONFIGURATION ---
BOT_TOKEN = "8711731953:AAHnVNJrkYE-NcnbecMgklNZM7R01oheb4k"
GEMINI_API_KEY = "AIzaSyAmxeeA3QNYRK6megtfNRv1eFvG5HZmpwU"
ADMIN_ID = 8503782525 

bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# Fast Model Configuration
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction="You are a super-fast study assistant. Give direct, clear, step-by-step solutions in Hinglish. Use bold text for final answers."
)

users = set()
user_states = {}

# Sabse purana syllabus data jo aapne manga tha
SYLLABUS = {
    "9": ["Number Systems", "Polynomials", "Lines and Angles", "Triangles", "Quadrilaterals", "Circles", "Heron's Formula", "Surface Areas"],
    "10": ["Real Numbers", "Polynomials", "Quadratic Equations", "Trigonometry", "Circles", "Statistics", "Probability"],
    "11": ["Sets", "Relations", "Trigonometry", "Linear Inequalities", "Limits", "Statistics"],
    "12": ["Matrices", "Determinants", "Integrals", "Differential Equations", "Vector Algebra", "3D Geometry"]
}

# --- 3. MAIN MENU ---
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
        types.InlineKeyboardButton("☎️ Contact Support", url="https://t.me/flaaxxx_run")
    )
    
    # Admin Panel (Directly visible to you)
    if uid == ADMIN_ID:
        markup.add(
            types.InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"),
            types.InlineKeyboardButton("📢 Send Broadcast", callback_data="admin_broadcast")
        )
    
    bot.send_message(uid, f"✨ **Welcome Back!**\nAapka ID: `{uid}`\nMain tayyar hoon, kya padhna hai?", reply_markup=markup, parse_mode="Markdown")

# --- 4. CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    cid = call.message.chat.id
    bot.answer_callback_query(call.id)

    if call.data == "admin_panel":
        bot.send_message(cid, f"📊 **Bot Stats**\nTotal Users: {len(users)}\nStatus: Online 🚀")

    elif call.data == "admin_broadcast":
        user_states[cid] = {"mode": "broadcast_waiting"}
        bot.send_message(cid, "📢 Message likhein jo sabko bhejna hai:")

    elif call.data == "study_main":
        markup = types.InlineKeyboardMarkup(row_width=2)
        for i in range(9, 13):
            markup.add(types.InlineKeyboardButton(f"Class {i}", callback_data=f"cls_{i}"))
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
        bot.send_message(cid, f"⏳ Class {cls}: {chap} ka solution nikal raha hoon...")
        try:
            res = model.generate_content(f"Explain Class {cls} {chap} summary and key points in Hinglish.")
            bot.send_message(cid, res.text)
        except: bot.send_message(cid, "❌ AI busy hai, thodi der baad try karein.")

    elif call.data.startswith("state_"):
        user_states[cid] = {"mode": call.data.split("_")[1]}
        bot.send_message(cid, "✅ Mode set! Ab sawal ya photo bhejein.")

# --- 5. FAST SEARCH & QUICK SOLUTION ---
@bot.message_handler(content_types=['photo', 'text'])
def handle_io(message):
    cid = message.chat.id
    mode = user_states.get(cid, {}).get("mode", "ai")

    # Admin Broadcast
    if mode == "broadcast_waiting" and cid == ADMIN_ID:
        for u in list(users):
            try: bot.send_message(u, f"📢 **NOTICE**\n\n{message.text}")
            except: pass
        bot.send_message(ADMIN_ID, "✅ Sabko bhej diya gaya!")
        user_states[cid] = {"mode": "ai"}
        return

    # Quick AI Solution
    if message.content_type == 'text' and not message.text.startswith('/'):
        bot.reply_to(message, "🔍 Searching quickly...")
        try:
            res = model.generate_content(message.text)
            bot.reply_to(message, res.text)
        except: bot.reply_to(message, "❌ AI error! Try later.")

    # Fast Image Scan
    elif message.content_type == 'photo':
        bot.reply_to(message, "⏳ Quick Scanning Image...")
        try:
            file_path = bot.get_file(message.photo[-1].file_id).file_path
            file = bot.download_file(file_path)
            img = {"mime_type": "image/jpeg", "data": file}
            prompt = "Extract text." if mode == "ocr" else "Solve this question step-by-step in Hinglish."
            res = model.generate_content([prompt, img])
            bot.reply_to(message, res.text)
        except: bot.reply_to(message, "❌ Photo error!")

# --- 6. RUN ---
if __name__ == "__main__":
    keep_alive()
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=0, timeout=40)
        except: time.sleep(5)
