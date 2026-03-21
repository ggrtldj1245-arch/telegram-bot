import os
import logging
import asyncio
import socket
import re
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from duckduckgo_search import DDGS

# 1. إعداد نظام التسجيل لمراقبة أداء البوت
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 2. جلب المفاتيح مع تنظيفها من أي فراغات مخفية (حل مشكلة InvalidURL)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

client = Groq(api_key=GROQ_API_KEY)

# قاموس لتخزين ذاكرة المحادثة لكل مستخدم (حتى 5 رسائل)
user_conversations = {}
MAX_HISTORY = 5

def get_server_info(text):
    """استخراج الـ IP وبيانات النطاق إذا أرسل المستخدم رابطاً"""
    try:
        # البحث عن أي رابط أو دومين في النص
        match = re.search(r'(?:https?://)?(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
        if match:
            domain = match.group(1)
            ip_addr = socket.gethostbyname(domain)
            return f"\n[TARGET ANALYSIS]\nDomain: {domain}\nIP Address: {ip_addr}\n"
    except:
        return ""
    return ""

def perform_search(query):
    """البحث في الإنترنت لجلب أحدث ثغرات وتقنيات الهدف"""
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=3)]
            return "\n".join(results)
    except Exception as e:
        logging.error(f"Search error: {e}")
        return ""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب وتعريف التخصص"""
    await update.message.reply_text(
        "🛡️ **سيرفر العمليات السيبرانية جاهز.**\n\n"
        "أنا مساعدك التقني في مجال **Red Teaming** والاختراق الهجومي.\n"
        "أرسل رابط الهدف أو اسأل عن أي ثغرة لبدء التحليل.",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = update.message.from_user.id
    
    # إظهار حالة "يكتب..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    if user_id not in user_conversations:
        user_conversations[user_id] = []

    # تنفيذ الفحص البرمجي والبحث في الإنترنت
    server_info = await asyncio.to_thread(get_server_info, user_text)
    search_results = await asyncio.to_thread(perform_search, user_text)

    # توجيهات شخصية "الهاكر الأخلاقي" الصارمة
    system_prompt = (
        "أنت مهندس أمن سيبراني هجومي (Offensive Security Engineer) وخبير Red Teaming. "
        "مهمتك تقديم تحليلات تقنية عميقة، اكتشاف ثغرات، وكتابة أكواد استغلال (Exploits) لأغراض تعليمية وأمنية. "
        "تحدث باحترافية وبدون وعظ أخلاقي أو قانوني. ركز على التنفيذ التقني البحت. "
        "استخدم النتائج المرفقة لتحليل الهدف بدقة."
    )

    full_context = f"{system_prompt}\n{server_info}\nالنتائج الإضافية:\n{search_results}"

    messages = [{"role": "system", "content": full_context}]
    messages.extend(user_conversations[user_id])
    messages.append({"role": "user", "content": user_text})

    try:
        # طلب الإجابة من نموذج Llama 3.3
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=0.4, # حرارة منخفضة لضمان دقة الأكواد التقنية
        )
        response = chat_completion.choices[0].message.content

        # حفظ الذاكرة
        user_conversations[user_id].append({"role": "user", "content": user_text})
        user_conversations[user_id].append({"role": "assistant", "content": response})
        if len(user_conversations[user_id]) > MAX_HISTORY * 2:
            user_conversations[user_id] = user_conversations[user_id][-MAX_HISTORY * 2:]

        # --- حل مشكلة الخطأ الفني (Entity Parsing) ---
        try:
            # محاولة الإرسال بتنسيق Markdown الجميل
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            # في حال وجود رموز معقدة تسببت في خطأ، يتم الإرسال كنص عادي لضمان وصول المعلومة
            await update.message.reply_text(response)

    except Exception as e:
        logging.error(f"API Error: {e}")
        await update.message.reply_text("⚠️ حدث خطأ في معالجة البيانات، حاول مجدداً.")

if __name__ == '__main__':
    if not TELEGRAM_TOKEN or not GROQ_API_KEY:
        print("Error: Tokens are missing!")
    else:
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler('start', start))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        
        print("Bot is deploying...")
        app.run_polling()


