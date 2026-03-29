import telebot
from telebot import types
import google.generativeai as genai
import os
import time
from flask import Flask
from threading import Thread

# --- 1. RENDER PORT FIX (Flask) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online with New API Key!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- 2. CONFIGURATION ---
# Aapki New API Key aur Bot Token
BOT_TOKEN = "8711731953:AAHnVNJrkYE-NcnbecMgklNZM7R01oheb4k"
GEMINI_API_KEY = "AIzaSyAmxeeA3QNYRK6megtfNRv1eFvG5HZmpwU"
ADMIN_ID = 8503782525 

bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. DYNAMIC MODEL SELECTION ---
# Isse 404 error nahi aayega
def get_model():
    models_to_try = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    for m in models_to_try:
        try:
            model = genai.GenerativeModel(m)
            # Test call to check if model is active
            model.generate_content("test")
            print(f"✅ Using Model: {m}")
            return model
        except:
            continue
    return genai.GenerativeModel('gemini-pro')

model = get_model()

users = set()
user_states = {}

SYLLABUS = {
    "9": ["Number Systems", "Polynomials", "Lines and Angles", "Triangles", "Circles"],
    "10": ["Real Numbers", "Polynomials", "Trigonometry", "Quadratic Equations", "Circles"],
    "11": ["Sets", "Trigonometry", "Permutations", "Limits", "Probability"],
    "12": ["Matrices", "Determinants", "Integrals", "Vectors", "3D Geometry"]
}

# --- 4. MAIN MENU ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    users.add(message.chat.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📖 Study (Syllabus & Chapters)", callback_data="study_main"),
        types.InlineKeyboardButton("📄 Photo to Text", callback_data="state_ocr"),
        types.InlineKeyboardButton("🔍 Scan and Search", callback_data="state_scan"),
        types.InlineKeyboardButton("🤖 AI Chat / Doubts", callback_data="state_ai")
    )
    bot.send_message(message.chat.id, "✨ **Bot Updated!** Nayi API Key set ho gayi hai.\nAb aap padhai shuru kar sakte hain.", reply_markup=markup, parse_mode="Markdown")

# --- 5. CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    cid = call.message.chat.id
    bot.answer_callback_query(call.id)

    if call.data == "study_main":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("📚 Summary", callback_data="mode_summary"),
                   types.InlineKeyboardButton("📝 Sample Paper", callback_data="mode_paper"))
        bot.edit_message_text("Kya chahiye?", cid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("mode_"):
        user_states[cid] = {"mode": call.data.split("_")[1]}
        markup = types.InlineKeyboardMarkup(row_width=2)
        for i in range(9, 13): markup.add(types.InlineKeyboardButton(f"Class {i}", callback_data=f"cls_{i}"))
        bot.edit_message_text("Class select karein:", cid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("cls_"):
        cls = call.data.split("_")[1]
        user_states[cid]["class"] = cls
        markup = types.InlineKeyboardMarkup(row_width=1)
        for ch in SYLLABUS.get(cls, []):
            markup.add(types.InlineKeyboardButton(ch, callback_data=f"ch_{ch}"))
        bot.edit_message_text(f"Class {cls} Chapters:", cid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("ch_"):
        chap, mode, cls = call.data.split("_")[1], user_states[cid].get("mode"), user_states[cid].get("class")
        bot.send_message(cid, f"🚀 AI processing Class {cls}: {chap}...")
        prompt = f"Explain Class {cls} {chap} with Summary and 5 QAs in Hinglish." if mode == "summary" else f"Create 10-question test for Class {cls} {chap}."
        try:
            res = model.generate_content(prompt)
            bot.send_message(cid, res.text)
        except: bot.send_message(cid, "⚠️ API Busy. Try again in 1 min.")

    elif call.data.startswith("state_"):
        user_states[cid] = {"mode": call.data.split("_")[1]}
        bot.send_message(cid, "✅ Mode set! Ab Photo ya Message bhejein.")

# --- 6. PHOTO & TEXT HANDLER ---
@bot.message_handler(content_types=['photo', 'text'])
def handle_io(message):
    cid = message.chat.id
    mode = user_states.get(cid, {}).get("mode", "ai")

    if message.content_type == 'photo':
        bot.reply_to(message, "⏳ Fast Scanning... Solution aa raha hai.")
        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            img = {"mime_type": "image/jpeg", "data": downloaded_file}
            
            prompt = "Extract text only." if mode == "ocr" else "Identify and solve all questions in this image step-by-step in Hinglish."
            response = model.generate_content([prompt, img])
            bot.reply_to(message, response.text)
        except Exception as e:
            bot.reply_to(message, "❌ Photo error! Please send a clear image.")
            
    elif not message.text.startswith('/'):
        bot.reply_to(message, "🔍 Searching...")
        try:
            response = model.generate_content(f"Explain clearly in Hinglish: {message.text}")
            bot.reply_to(message, response.text)
        except:
            bot.reply_to(message, "❌ AI is currently unavailable. Try later.")

# --- 7. RUN BOT ---
if __name__ == "__main__":
    keep_alive()
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=0, timeout=60)
        except:
            time.sleep(5)
