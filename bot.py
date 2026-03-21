import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from duckduckgo_search import DDGS

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# الحصول على المفاتيح من متغيرات البيئة
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك! أنا بوت ذكي مدعوم بـ Groq و DuckDuckGo. كيف يمكنني مساعدتك اليوم؟")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # البحث في DuckDuckGo للحصول على معلومات حديثة
    search_results = ""
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(user_text, max_results=3)]
            search_results = "\n".join(results)
    except Exception as e:
        logging.error(f"Error searching DDG: {e}")

    # بناء السياق لـ Groq
    prompt = f"User asked: {user_text}\n\nSearch results for context:\n{search_results}\n\nPlease provide a helpful response in Arabic."
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
        )
        response = chat_completion.choices[0].message.content
        await update.message.reply_text(response)
    except Exception as e:
        logging.error(f"Error with Groq API: {e}")
        await update.message.reply_text("عذراً، حدث خطأ أثناء معالجة طلبك.")

if __name__ == '__main__':
    if not TELEGRAM_TOKEN or not GROQ_API_KEY:
        logging.error("TELEGRAM_TOKEN or GROQ_API_KEY not set!")
    else:
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        start_handler = CommandHandler('start', start)
        msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
        
        application.add_handler(start_handler)
        application.add_handler(msg_handler)
        
        application.run_polling()
