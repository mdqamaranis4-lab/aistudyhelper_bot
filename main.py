import telebot
from telebot import types
import google.generativeai as genai
import os
import time
from flask import Flask
from threading import Thread

# --- 1. RENDER PORT SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online with Support Feature!"

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

# Gemini Connection
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    print(f"API Error: {e}")

users = set()
user_states = {}

# --- 3. MAIN MENU (Support & Admin Fixed) ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    users.add(message.chat.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Study & AI Buttons
    markup.add(
        types.InlineKeyboardButton("📖 Study (Syllabus)", callback_data="study_main"),
        types.InlineKeyboardButton("📄 Photo to Text", callback_data="state_ocr"),
        types.InlineKeyboardButton("🔍 Scan and Search", callback_data="state_scan"),
        types.InlineKeyboardButton("🤖 AI Chat", callback_data="state_ai")
    )
    
    # Support Button (Direct Link to you)
    markup.add(types.InlineKeyboardButton("☎️ Contact Support (@flaaxxx_run)", url="https://t.me/flaaxxx_run"))
    
    # Admin Panel (Only for you)
    if message.chat.id == ADMIN_ID:
        markup.add(
            types.InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"),
            types.InlineKeyboardButton("📢 Send Broadcast", callback_data="admin_broadcast")
        )
    
    bot.send_message(message.chat.id, "✨ **Bot Active & Updated!**\nNiche diye gaye options use karein.", reply_markup=markup, parse_mode="Markdown")

# --- 4. CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    cid = call.message.chat.id
    bot.answer_callback_query(call.id)

    if call.data == "admin_panel":
        bot.send_message(cid, f"📊 **Bot Statistics**\n\nTotal Active Users: {len(users)}\nAPI Key: Active\nAdmin Status: Verified ✅")

    elif call.data == "admin_broadcast":
        user_states[cid] = {"mode": "broadcast_waiting"}
        bot.send_message(cid, "📢 **Broadcast Mode:**\nApna message likhein jo sabhi users ko bhejna hai:")

    elif call.data == "study_main":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("📚 Summary", callback_data="state_ai"),
                   types.InlineKeyboardButton("⬅️ Back", callback_data="back"))
        bot.edit_message_text("Topic ya sawal ka naam likhein:", cid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("state_"):
        user_states[cid] = {"mode": call.data.split("_")[1]}
        bot.send_message(cid, "✅ Mode Active! Ab aap photo ya text bhej sakte hain.")

    elif call.data == "back":
        start_cmd(call.message)

# --- 5. MESSAGE HANDLER ---
@bot.message_handler(content_types=['photo', 'text'])
def handle_io(message):
    cid = message.chat.id
    state_data = user_states.get(cid, {})
    mode = state_data.get("mode", "ai")

    # Admin Broadcast execution
    if mode == "broadcast_waiting" and cid == ADMIN_ID:
        count = 0
        for user in list(users):
            try:
                bot.send_message(user, f"📢 **IMPORTANT UPDATE**\n\n{message.text}")
                count += 1
            except: pass
        bot.send_message(ADMIN_ID, f"✅ Success! Message {count} users ko bhej diya gaya.")
        user_states[cid] = {"mode": "ai"}
        return

    # Text Query
    if message.content_type == 'text' and not message.text.startswith('/'):
        bot.reply_to(message, "🔍 Searching...")
        try:
            response = model.generate_content(f"Explain clearly in Hinglish: {message.text}")
            bot.reply_to(message, response.text)
        except:
            bot.reply_to(message, "❌ AI Limit reached. Try again in 1 minute.")

    # Photo Query
    elif message.content_type == 'photo':
        bot.reply_to(message, "⏳ Reading Image...")
        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            img = {"mime_type": "image/jpeg", "data": downloaded_file}
            response = model.generate_content(["Solve this problem step-by-step in Hinglish.", img])
            bot.reply_to(message, response.text)
        except:
            bot.reply_to(message, "❌ Photo error! Make sure the image is clear.")

# --- 6. RUN BOT ---
if __name__ == "__main__":
    keep_alive()
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=0, timeout=60)
        except: time.sleep(5)
