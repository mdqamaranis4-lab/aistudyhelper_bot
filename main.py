import telebot
from telebot import types
import google.generativeai as genai
import os
from flask import Flask
from threading import Thread

# --- RENDER PORT FIX ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Alive!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- CONFIG ---
BOT_TOKEN = "8711731953:AAHnVNJrkYE-NcnbecMgklNZM7R01oheb4k"
GEMINI_API_KEY = "AIzaSyAFEoQa_yatk2tphW4paIAvjOSc054UBjk"
ADMIN_ID = 8503782525 

bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

users = set()
user_states = {}

# --- DETAILED SYLLABUS ---
SYLLABUS = {
    "9": ["Number Systems", "Polynomials", "Coordinate Geometry", "Linear Equations", "Lines and Angles", "Triangles", "Quadrilaterals", "Circles", "Heron's Formula", "Surface Areas"],
    "10": ["Real Numbers", "Polynomials", "Pair of Linear Equations", "Quadratic Equations", "Arithmetic Progressions", "Triangles", "Coordinate Geometry", "Trigonometry", "Circles", "Statistics"],
    "11": ["Sets", "Relations & Functions", "Trigonometry", "Linear Inequalities", "Permutations", "Conic Sections", "Limits and Derivatives", "Statistics", "Probability"],
    "12": ["Relations & Functions", "Inverse Trig", "Matrices", "Determinants", "Continuity & Differentiability", "Integrals", "Differential Equations", "Vector Algebra", "3D Geometry"]
}

# --- MAIN MENU ---
@bot.message_handler(commands=['start'])
def start(message):
    users.add(message.chat.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # "Study 📖" Button as the main entry
    study_btn = types.InlineKeyboardButton("📖 Study (Syllabus & Chapters)", callback_data="study_main")
    
    # Utility Buttons
    ocr_btn = types.InlineKeyboardButton("📄 Photo to Text", callback_data="state_ocr")
    scan_btn = types.InlineKeyboardButton("🔍 Scan and Search", callback_data="state_scan")
    ai_btn = types.InlineKeyboardButton("🤖 AI Chat / Doubts", callback_data="state_ai")
    
    markup.add(study_btn, ocr_btn, scan_btn, ai_btn)
    
    if message.chat.id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"))
    
    bot.send_message(message.chat.id, f"Namaste {message.from_user.first_name}! Main aapka AI Study Assistant hoon. Padhai shuru karne ke liye niche button dabayein.", reply_markup=markup)

# --- CALLBACK HANDLER ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    cid = call.message.chat.id
    bot.answer_callback_query(call.id)

    # 1. Main Study Menu
    if call.data == "study_main":
        markup = types.InlineKeyboardMarkup(row_width=2)
        btns = [
            types.InlineKeyboardButton("📚 Summary & Q/A", callback_data="mode_summary"),
            types.InlineKeyboardButton("📝 Sample Paper", callback_data="mode_paper"),
            types.InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")
        ]
        markup.add(btns[0], btns[1])
        markup.add(btns[2])
        bot.edit_message_text("Aap kya karna chahte hain?", cid, call.message.message_id, reply_markup=markup)

    # 2. Mode Selection (Summary or Paper)
    elif call.data.startswith("mode_"):
        mode = call.data.split("_")[1]
        user_states[cid] = {"mode": mode}
        markup = types.InlineKeyboardMarkup(row_width=2)
        classes = [types.InlineKeyboardButton(f"Class {i}", callback_data=f"cls_{i}") for i in range(9, 13)]
        markup.add(*classes)
        bot.edit_message_text("Apni Class select karein:", cid, call.message.message_id, reply_markup=markup)

    # 3. Class Selection -> Shows Detailed Chapters
    elif call.data.startswith("cls_"):
        cls = call.data.split("_")[1]
        user_states[cid]["class"] = cls
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        chapters = SYLLABUS.get(cls, ["General Math"])
        # Sirf pehle 8-10 chapters dikhate hain taaki button list lambi na ho
        for ch in chapters[:10]: 
            markup.add(types.InlineKeyboardButton(ch, callback_data=f"ch_{ch}"))
            
        markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="study_main"))
        bot.edit_message_text(f"Class {cls} Syllabus (Chapters):", cid, call.message.message_id, reply_markup=markup)

    # 4. Final AI Call for Chapters
    elif call.data.startswith("ch_"):
        chap = call.data.split("_")[1]
        mode = user_states[cid].get("mode")
        cls = user_states[cid].get("class")
        
        bot.send_message(cid, f"⏳ AI is analyzing: Class {cls} - {chap}...")
        
        if mode == "summary":
            p = f"Explain Class {cls} {chap} with a clear summary and 5 most important Questions & Answers in Hinglish."
        else:
            p = f"Generate a 10-question Sample Practice Paper for Class {cls} {chap} with solutions in Hinglish."
            
        res = model.generate_content(p)
        bot.send_message(cid, res.text)

    # 5. Other States
    elif call.data.startswith("state_"):
        state = call.data.split("_")[1]
        user_states[cid] = {"mode": state}
        msg = "📸 Kripya Photo bhejein." if state in ["ocr", "scan"] else "⌨️ Apna sawal likh kar bhejein."
        bot.send_message(cid, msg)

    elif call.data == "back_to_main":
        start(call.message)

# --- BROADCAST & PHOTO HANDLER --- (Same as before)
@bot.message_handler(content_types=['photo', 'text'])
def handle_input(message):
    cid = message.chat.id
    state = user_states.get(cid, {}).get("mode", "ai")
    
    if message.content_type == 'photo':
        bot.reply_to(message, "⏳ Processing...")
        fid = message.photo[-1].file_id
        file = bot.download_file(bot.get_file(fid).file_path)
        img = {"mime_type": "image/jpeg", "data": file}
        prompt = "OCR this image" if state == "ocr" else "Solve this study problem step by step in Hinglish."
        res = model.generate_content([prompt, img])
        bot.reply_to(message, res.text)
    elif not message.text.startswith('/'):
        res = model.generate_content(f"Explain in Hinglish: {message.text}")
        bot.reply_to(message, res.text)

if __name__ == "__main__":
    keep_alive()
    bot.polling(none_stop=True)
