import telebot
from telebot import types
import google.generativeai as genai
import os
from flask import Flask
from threading import Thread

# --- RENDER PORT FIX (FLASK SETUP) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Running Successfully!"

def run():
    # Render hamesha port 10000 ya 8080 expect karta hai
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- BOT CONFIGURATION ---
BOT_TOKEN = "8711731953:AAHnVNJrkYE-NcnbecMgklNZM7R01oheb4k"
GEMINI_API_KEY = "AIzaSyAFEoQa_yatk2tphW4paIAvjOSc054UBjk"
ADMIN_ID = 8503782525 

bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

users = set() 
user_data = {}

# --- SYLLABUS DATA ---
SYLLABUS = {
    "9": ["Ch 1: Number Systems", "Ch 2: Polynomials", "Ch 6: Lines and Angles", "Ch 10: Circles"],
    "10": ["Ch 1: Real Numbers", "Ch 2: Polynomials", "Ch 8: Trigonometry", "Ch 10: Circles"],
    "11": ["Ch 1: Sets", "Ch 3: Trig Functions", "Ch 7: Permutations", "Ch 13: Limits"],
    "12": ["Ch 1: Relations & Functions", "Ch 3: Matrices", "Ch 5: Continuity", "Ch 7: Integrals"]
}

# --- MAIN MENU ---
@bot.message_handler(commands=['start'])
def main_menu(message):
    users.add(message.chat.id) 
    markup = types.InlineKeyboardMarkup(row_width=1)
    btns = [
        types.InlineKeyboardButton("📄 Photo to Text", callback_data="ocr"),
        types.InlineKeyboardButton("🔍 Scan and Search", callback_data="scan"),
        types.InlineKeyboardButton("🤖 AI Generation", callback_data="ai_gen"),
        types.InlineKeyboardButton("📚 Summary & Q/A", callback_data="class_select"),
        types.InlineKeyboardButton("📝 Sample Paper", callback_data="sample_paper")
    ]
    if message.chat.id == ADMIN_ID:
        btns.append(types.InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"))
    
    markup.add(*btns)
    bot.send_message(message.chat.id, f"Namaste {message.from_user.first_name}! Main AI Assistant hoon.", reply_markup=markup)

# --- ADMIN & BROADCAST ---
@bot.message_handler(commands=['broadcast'])
def broadcast_handler(message):
    if message.chat.id == ADMIN_ID:
        msg_text = message.text.replace('/broadcast', '').strip()
        if not msg_text:
            bot.reply_to(message, "Usage: /broadcast [Message]")
            return
        success = 0
        for user in users:
            try:
                bot.send_message(user, f"📢 **NOTICE BY ADMIN**\n\n{msg_text}")
                success += 1
            except: pass
        bot.send_message(ADMIN_ID, f"✅ Sent to {success} users.")

@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def admin_info(call):
    bot.send_message(call.message.chat.id, f"📊 Stats: {len(users)} Users\nUse /broadcast [msg]")

# --- CLASS & CHAPTER SELECTION ---
@bot.callback_query_handler(func=lambda call: call.data in ["class_select", "sample_paper"])
def choose_class(call):
    user_data[call.message.chat.id] = {"action": call.data}
    markup = types.InlineKeyboardMarkup(row_width=2)
    classes = [types.InlineKeyboardButton(f"Class {i}", callback_data=f"cls_{i}") for i in range(9, 13)]
    markup.add(*classes)
    bot.edit_message_text("Class select karein:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cls_"))
def choose_chapter(call):
    cls_num = call.data.split("_")[1]
    user_data[call.message.chat.id]["class"] = cls_num
    markup = types.InlineKeyboardMarkup(row_width=1)
    chapters = SYLLABUS.get(cls_num, ["General Study"])
    for ch in chapters:
        markup.add(types.InlineKeyboardButton(ch, callback_data=f"ch_{ch}"))
    bot.edit_message_text(f"Class {cls_num} Chapters:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ch_"))
def final_ai_call(call):
    chat_id = call.message.chat.id
    chap = call.data.split("_")[1]
    cls = user_data[chat_id]["class"]
    action = user_data[chat_id]["action"]
    bot.send_message(chat_id, "🔍 AI is generating...")
    prompt = f"Explain Class {cls} {chap}. Summary + 5 QAs in Hinglish." if action == "class_select" else f"Create 10-question practice test for Class {cls} {chap} in Hinglish."
    response = model.generate_content(prompt)
    bot.send_message(chat_id, response.text)

# --- PHOTO HANDLER ---
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.reply_to(message, "📸 Analyzing photo...")
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    img_data = {"mime_type": "image/jpeg", "data": downloaded_file}
    response = model.generate_content(["Solve this step by step in Hinglish.", img_data])
    bot.reply_to(message, response.text)

# --- START BOT & FLASK ---
if __name__ == "__main__":
    keep_alive() # Starts Flask on a separate thread
    print("Bot is LIVE!")
    bot.polling(none_stop=True)
