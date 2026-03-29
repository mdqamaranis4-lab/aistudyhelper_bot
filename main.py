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
def home(): return "Bot is Online!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- 2. CONFIGURATION ---
BOT_TOKEN = "8711731953:AAHnVNJrkYE-NcnbecMgklNZM7R01oheb4k"
GEMINI_API_KEY = "AIzaSyAFEoQa_yatk2tphW4paIAvjOSc054UBjk"
ADMIN_ID = 8503782525 

bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# AI ko "Fast & Clear" banane ke liye System Instruction
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    generation_config={"temperature": 0.7, "top_p": 0.9, "max_output_tokens": 2048},
    system_instruction="You are a Fast AI Study Assistant. Provide clear, step-by-step solutions in Hinglish. Use bold text for headings and bullet points for steps. If an image is provided, identify the question and solve it immediately."
)

users = set() 
user_states = {}

SYLLABUS = {
    "9": ["Number Systems", "Polynomials", "Lines and Angles", "Triangles", "Circles", "Surface Areas"],
    "10": ["Real Numbers", "Polynomials", "Quadratic Equations", "Trigonometry", "Circles", "Statistics"],
    "11": ["Sets", "Trigonometry", "Permutations", "Limits", "Probability"],
    "12": ["Matrices", "Determinants", "Integrals", "Differential Equations", "Vector Algebra"]
}

# --- 3. HELPER FUNCTION FOR FAST AI ---
def get_ai_response(prompt_data):
    for i in range(3): # 3 baar retry karega agar busy ho
        try:
            response = model.generate_content(prompt_data)
            return response.text
        except Exception as e:
            if "429" in str(e):
                time.sleep(3)
                continue
            return f"⚠️ Error: {str(e)}"
    return "❌ Server Busy. Please try again in 1 minute."

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
    if message.chat.id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"))
    
    bot.send_message(message.chat.id, f"Namaste {message.from_user.first_name}! Main Fast AI Assistant hoon. Kya help chahiye?", reply_markup=markup)

# --- 5. CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    cid = call.message.chat.id
    bot.answer_callback_query(call.id)

    if call.data == "study_main":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("📚 Summary", callback_data="mode_summary"),
                   types.InlineKeyboardButton("📝 Sample Paper", callback_data="mode_paper"))
        markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="back_to_main"))
        bot.edit_message_text("Kya chahiye?", cid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("mode_"):
        user_states[cid] = {"mode": call.data.split("_")[1]}
        markup = types.InlineKeyboardMarkup(row_width=2)
        for i in range(9, 13): markup.add(types.InlineKeyboardButton(f"Class {i}", callback_data=f"cls_{i}"))
        bot.edit_message_text("Class chunein:", cid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("cls_"):
        cls = call.data.split("_")[1]
        user_states[cid]["class"] = cls
        markup = types.InlineKeyboardMarkup(row_width=1)
        for ch in SYLLABUS.get(cls, [])[:8]:
            markup.add(types.InlineKeyboardButton(ch, callback_data=f"ch_{ch}"))
        bot.edit_message_text(f"Class {cls} Chapters:", cid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("ch_"):
        chap, mode, cls = call.data.split("_")[1], user_states[cid].get("mode"), user_states[cid].get("class")
        bot.send_message(cid, f"🚀 Generating {mode} for {chap}...")
        prompt = f"Provide Class {cls} {chap} summary and 5 QAs in Hinglish." if mode == "summary" else f"Create 10-question test for Class {cls} {chap}."
        bot.send_message(cid, get_ai_response(prompt))

    elif call.data.startswith("state_"):
        user_states[cid] = {"mode": call.data.split("_")[1]}
        bot.send_message(cid, "✅ Mode set! Ab Photo ya Message bhejein.")

    elif call.data == "back_to_main": start_cmd(call.message)
    elif call.data == "admin_panel" and cid == ADMIN_ID:
        bot.send_message(cid, f"📊 Users: {len(users)}\nUse `/broadcast [msg]`")

# --- 6. PHOTO & TEXT HANDLER ---
@bot.message_handler(content_types=['photo', 'text'])
def handle_io(message):
    cid = message.chat.id
    mode = user_states.get(cid, {}).get("mode", "ai")
    
    if message.content_type == 'photo':
        bot.reply_to(message, "⏳ Fast Scanning... Solution aa raha hai.")
        try:
            file = bot.download_file(bot.get_file(message.photo[-1].file_id).file_path)
            img = {"mime_type": "image/jpeg", "data": file}
            prompt = "Extract text only." if mode == "ocr" else "Identify and solve all questions in this image step-by-step in Hinglish."
            bot.reply_to(message, get_ai_response([prompt, img]))
        except: bot.reply_to(message, "❌ Photo error. Please try again.")
    elif not message.text.startswith('/'):
        bot.reply_to(message, "🔍 Searching...")
        bot.reply_to(message, get_ai_response(f"Explain clearly in Hinglish: {message.text}"))

# --- 7. RUN BOT ---
if __name__ == "__main__":
    keep_alive()
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=0, timeout=40)
        except: time.sleep(5)
