import telebot
from telebot import types
import google.generativeai as genai

# --- CONFIGURATION ---
BOT_TOKEN = "8711731953:AAHnVNJrkYE-NcnbecMgklNZM7R01oheb4k"
GEMINI_API_KEY = "AIzaSyAFEoQa_yatk2tphW4paIAvjOSc054UBjk"
ADMIN_ID = 8503782525  # Aapki Updated Admin ID

bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Database (Users list for broadcast)
users = set() 
user_data = {}

# --- SYLLABUS DATA ---
SYLLABUS = {
    "9": ["Ch 1: Number Systems", "Ch 2: Polynomials", "Ch 6: Lines and Angles", "Ch 10: Circles"],
    "10": ["Ch 1: Real Numbers", "Ch 2: Polynomials", "Ch 8: Trigonometry", "Ch 10: Circles"],
    "11": ["Ch 1: Sets", "Ch 3: Trig Functions", "Ch 7: Permutations", "Ch 13: Limits"],
    "12": ["Ch 1: Relations & Functions", "Ch 3: Matrices", "Ch 5: Continuity", "Ch 7: Integrals"]
}

# --- 1. MAIN MENU ---
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
    # Admin check
    if message.chat.id == ADMIN_ID:
        btns.append(types.InlineKeyboardButton("⚙️ Admin Panel (Stats)", callback_data="admin_panel"))
    
    markup.add(*btns)
    bot.send_message(message.chat.id, f"Namaste {message.from_user.first_name}! Main aapka AI Study Assistant hoon. Kya help chahiye?", reply_markup=markup)

# --- 2. ADMIN & BROADCAST ---
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
                bot.send_message(user, f"📢 **ANNouncement BY ADMIN** 📢\n\n{msg_text}", parse_mode="Markdown")
                success += 1
            except: pass
        bot.send_message(ADMIN_ID, f"✅ Message sent to {success} users.")
    else:
        bot.reply_to(message, "❌ Sirf Admin hi broadcast kar sakta hai.")

@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def admin_info(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"📊 **Bot Stats**\n\nTotal Users: {len(users)}\nAdmin ID: {ADMIN_ID}\n\nBroadcast karne ke liye likhein: `/broadcast Hello Students`")

# --- 3. CLASS & CHAPTER FLOW ---
@bot.callback_query_handler(func=lambda call: call.data in ["class_select", "sample_paper"])
def choose_class(call):
    user_data[call.message.chat.id] = {"action": call.data}
    markup = types.InlineKeyboardMarkup(row_width=2)
    classes = [types.InlineKeyboardButton(f"Class {i}", callback_data=f"cls_{i}") for i in range(9, 13)]
    markup.add(*classes)
    bot.edit_message_text("Apni Class select karein:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cls_"))
def choose_chapter(call):
    cls_num = call.data.split("_")[1]
    user_data[call.message.chat.id]["class"] = cls_num
    markup = types.InlineKeyboardMarkup(row_width=1)
    chapters = SYLLABUS.get(cls_num, ["General Study"])
    for ch in chapters:
        markup.add(types.InlineKeyboardButton(ch, callback_data=f"ch_{ch}"))
    markup.add(types.InlineKeyboardButton("⬅️ Back to Classes", callback_data="class_select"))
    bot.edit_message_text(f"Class {cls_num} ke Chapters:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ch_"))
def final_ai_call(call):
    chat_id = call.message.chat.id
    chap = call.data.split("_")[1]
    cls = user_data[chat_id]["class"]
    action = user_data[chat_id]["action"]
    
    bot.edit_message_text("🔍 AI is generating your material...", chat_id, call.message.message_id)
    
    prompt = f"Student Class: {cls}, Chapter: {chap}. "
    if action == "class_select":
        prompt += "Explain this chapter with a summary and 5 important Questions & Answers in Hinglish."
    else:
        prompt += "Create a 10-question practice test paper for this chapter in Hinglish."

    try:
        response = model.generate_content(prompt)
        bot.send_message(chat_id, response.text)
    except:
        bot.send_message(chat_id, "Gemini API busy hai, thodi der baad try karein.")

# --- 4. PHOTO/OCR HANDLER ---
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    users.add(message.chat.id)
    bot.reply_to(message, "📸 Photo mil gayi! AI is solving it...")
    
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    img_data = {"mime_type": "image/jpeg", "data": downloaded_file}
    response = model.generate_content(["Solve this study material/question in Hinglish step by step.", img_data])
    bot.reply_to(message, response.text)

@bot.callback_query_handler(func=lambda call: call.data in ["ocr", "scan", "ai_gen"])
def other_btns(call):
    msg = "Aap book ki photo bhejein, main solution dunga." if call.data != "ai_gen" else "Topic ka naam likh kar bhejein, main explain kar dunga."
    bot.send_message(call.message.chat.id, msg)

print("Bot is ready and running!")
bot.polling(none_stop=True)
