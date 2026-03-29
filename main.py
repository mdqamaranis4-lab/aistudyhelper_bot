import telebot
from telebot import types
import google.generativeai as genai
import os
import time
from flask import Flask
from threading import Thread

# --- 1. RENDER PORT SERVER (To keep it alive) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online and Running!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. CONFIGURATION ---
BOT_TOKEN = "8711731953:AAHnVNJrkYE-NcnbecMgklNZM7R01oheb4k"
GEMINI_API_KEY = "AIzaSyAFEoQa_yatk2tphW4paIAvjOSc054UBjk"
ADMIN_ID = 8503782525 

bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

users = set() 
user_states = {}

# --- 3. SYLLABUS DATA ---
SYLLABUS = {
    "9": ["Number Systems", "Polynomials", "Coordinate Geometry", "Linear Equations", "Lines and Angles", "Triangles", "Quadrilaterals", "Circles", "Heron's Formula", "Surface Areas"],
    "10": ["Real Numbers", "Polynomials", "Pair of Linear Equations", "Quadratic Equations", "Arithmetic Progressions", "Triangles", "Coordinate Geometry", "Trigonometry", "Circles", "Statistics"],
    "11": ["Sets", "Relations & Functions", "Trigonometry", "Linear Inequalities", "Permutations", "Conic Sections", "Limits and Derivatives", "Statistics", "Probability"],
    "12": ["Relations & Functions", "Inverse Trig", "Matrices", "Determinants", "Continuity & Differentiability", "Integrals", "Differential Equations", "Vector Algebra", "3D Geometry"]
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
    if message.chat.id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"))
    
    bot.send_message(message.chat.id, f"Namaste {message.from_user.first_name}! Main aapka Study Assistant hoon. Kya padhna chahte hain?", reply_markup=markup)

# --- 5. CALLBACK HANDLERS (Buttons) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    cid = call.message.chat.id
    bot.answer_callback_query(call.id)

    if call.data == "study_main":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📚 Summary & Q/A", callback_data="mode_summary"),
            types.InlineKeyboardButton("📝 Sample Paper", callback_data="mode_paper")
        )
        markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="back_to_main"))
        bot.edit_message_text("Option chunein:", cid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("mode_"):
        mode = call.data.split("_")[1]
        user_states[cid] = {"mode": mode}
        markup = types.InlineKeyboardMarkup(row_width=2)
        for i in range(9, 13):
            markup.add(types.InlineKeyboardButton(f"Class {i}", callback_data=f"cls_{i}"))
        bot.edit_message_text("Class select karein:", cid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("cls_"):
        cls = call.data.split("_")[1]
        user_states[cid]["class"] = cls
        markup = types.InlineKeyboardMarkup(row_width=1)
        for ch in SYLLABUS.get(cls, [])[:10]:
            markup.add(types.InlineKeyboardButton(ch, callback_data=f"ch_{ch}"))
        markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="study_main"))
        bot.edit_message_text(f"Class {cls} Chapters:", cid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("ch_"):
        chap = call.data.split("_")[1]
        mode = user_states[cid].get("mode", "summary")
        cls = user_states[cid].get("class", "10")
        bot.send_message(cid, f"⏳ AI kaam kar raha hai (Class {cls}: {chap})...")
        
        prompt = f"Explain Class {cls} {chap}. Summary + 5 QAs in Hinglish." if mode == "summary" else f"10-question test paper for Class {cls} {chap} with solutions in Hinglish."
        try:
            res = model.generate_content(prompt)
            bot.send_message(cid, res.text)
        except:
            bot.send_message(cid, "⚠️ AI limit full hai, 1 minute baad try karein.")

    elif call.data.startswith("state_"):
        state = call.data.split("_")[1]
        user_states[cid] = {"mode": state}
        msg = "📸 Kripya Photo bhejein." if state in ["ocr", "scan"] else "⌨️ Sawal likh kar bhejein."
        bot.send_message(cid, msg)

    elif call.data == "back_to_main":
        start_cmd(call.message)

    elif call.data == "admin_panel" and cid == ADMIN_ID:
        bot.send_message(cid, f"📊 Total Users: {len(users)}\nBroadcast ke liye likhein: `/broadcast Hello Students`")

# --- 6. ADMIN BROADCAST ---
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.chat.id == ADMIN_ID:
        txt = message.text.replace('/broadcast', '').strip()
        if not txt: return
        for u in users:
            try: bot.send_message(u, f"📢 **NOTICE**\n\n{txt}")
            except: pass
        bot.send_message(ADMIN_ID, "✅ Broadcast Done!")

# --- 7. PHOTO & DOUBT HANDLER ---
@bot.message_handler(content_types=['photo', 'text'])
def handle_io(message):
    cid = message.chat.id
    mode = user_states.get(cid, {}).get("mode", "ai")
    
    if message.content_type == 'photo':
        bot.reply_to(message, "⏳ Reading Image...")
        try:
            fid = message.photo[-1].file_id
            file = bot.download_file(bot.get_file(fid).file_path)
            img = {"mime_type": "image/jpeg", "data": file}
            prompt = "Extract text only." if mode == "ocr" else "Solve this question step-by-step in Hinglish."
            res = model.generate_content([prompt, img])
            bot.reply_to(message, res.text)
        except: bot.reply_to(message, "❌ Photo error!")
    elif not message.text.startswith('/'):
        bot.reply_to(message, "🔍 Searching...")
        res = model.generate_content(f"Explain in Hinglish: {message.text}")
        bot.reply_to(message, res.text)

# --- 8. RUN BOT WITH RESTART LOGIC ---
if __name__ == "__main__":
    keep_alive()
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=0, timeout=40)
        except Exception as e:
            print(f"Restarting... Error: {e}")
            time.sleep(5)
