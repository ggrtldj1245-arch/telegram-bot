import os
import logging
import asyncio
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from duckduckgo_search import DDGS

# إعداد التسجيل لمتابعة الأخطاء
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# الحصول على المفاتيح من متغيرات البيئة مع تنظيفها من الفراغات
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

client = Groq(api_key=GROQ_API_KEY)

# قاموس لتخزين ذاكرة المحادثة لكل مستخدم
user_conversations = {}
MAX_HISTORY = 5 # نحتفظ بآخر 5 أسئلة وأجوبة لكل مستخدم

def perform_search(query):
    """دالة البحث في الإنترنت عبر DuckDuckGo"""
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=3)]
            return "\n".join(results)
    except Exception as e:
        logging.error(f"DDG Search Error: {e}")
        return ""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الرد على أمر /start"""
    welcome_msg = (
        "أهلاً بك! 🛡️💻\n\n"
        "أنا مساعدك الذكي، مهندس متخصص في **الأمن السيبراني والهجوم والاختراق (Penetration Testing)**.\n"
        "أستطيع مساعدتك في تحليل الثغرات، حماية الأنظمة، تقديم استشارات أمنية متقدمة، وشرح تقنيات الهاكر الأخلاقي مع جلب أحدث المعلومات من الإنترنت.\n\n"
        "أرسل /help لمعرفة الأوامر، أو اطرح سؤالك التقني والأمني مباشرة!"
    )
    await update.message.reply_text(welcome_msg, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الرد على أمر /help"""
    help_text = (
        "🛠 **الأوامر المتاحة:**\n\n"
        "• /start - بدء المحادثة\n"
        "• /help - عرض قائمة الأوامر المتاحة\n"
        "• /clear - مسح ذاكرة المحادثة للبدء في تحليل أمني جديد\n\n"
        "فقط أرسل أي استفسار أمني وسأقوم بالرد عليك!"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر مسح ذاكرة المحادثة"""
    user_id = update.message.from_user.id
    if user_id in user_conversations:
        user_conversations[user_id] = []
    await update.message.reply_text("🧹 تم مسح السجلات بنجاح! السيرفر جاهز للبدء في موضوع أو تحليل جديد.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية والرد عليها"""
    user_text = update.message.text
    user_id = update.message.from_user.id
    
    # إظهار حالة "يكتب..." للمستخدم أثناء المعالجة
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # تهيئة ذاكرة المستخدم إذا كان يتحدث لأول مرة
    if user_id not in user_conversations:
        user_conversations[user_id] = []

    # تشغيل البحث بشكل غير متزامن في الخلفية لعدم إيقاف البوت
    search_results = await asyncio.to_thread(perform_search, user_text)

    # شخصية البوت (المهندس السيبراني)
    system_prompt = (
        "أنت خبير ومستشار متمرس في الأمن السيبراني (Cybersecurity) ومهندس محترف متخصص في الهجوم والاختراق "
        "واختبار الاختراق (Penetration Testing & Offensive Security). "
        "تتحدث اللغة العربية بطلاقة واحترافية وبمصطلحات تقنية دقيقة. قدم إجابات عميقة، تقنية، وعملية تفيد المبرمجين "
        "ومديري الأنظمة والمهتمين بالأمن. "
        "التزم دائماً بالمعايير الأخلاقية (Ethical Hacking) ونبه على أن الاستخدام يجب أن يكون لأغراض تعليمية وقانونية فقط. "
    )
    if search_results:
        system_prompt += f"\nإليك بعض المعلومات الحديثة من الإنترنت التي قد تساعدك في تحليلك وإجابتك:\n{search_results}"

    # تجميع سياق المحادثة (شخصية البوت + التاريخ السابق + السؤال الجديد)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(user_conversations[user_id])
    messages.append({"role": "user", "content": user_text})

    try:
        # إرسال الطلب إلى Groq
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=0.6, # تقليل الحرارة قليلاً لتكون الإجابات التقنية أكثر دقة وصرامة
        )
        response = chat_completion.choices[0].message.content

        # تحديث ذاكرة المحادثة بالسؤال والإجابة الجديدة
        user_conversations[user_id].append({"role": "user", "content": user_text})
        user_conversations[user_id].append({"role": "assistant", "content": response})
        
        # الاحتفاظ بآخر 5 أسئلة وأجوبة فقط
        if len(user_conversations[user_id]) > MAX_HISTORY * 2:
            user_conversations[user_id] = user_conversations[user_id][-MAX_HISTORY * 2:]

        # إرسال الرد للمستخدم في تليجرام
        try:
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(response)

    except Exception as e:
        logging.error(f"Error with Groq API: {e}")
        await update.message.reply_text("عذراً، حدث خطأ في الاتصال بالخادم أثناء معالجة البيانات. حاول مرة أخرى لاحقاً.")

if __name__ == '__main__':
    if not TELEGRAM_TOKEN or not GROQ_API_KEY:
        logging.error("TELEGRAM_TOKEN or GROQ_API_KEY is missing! Bot cannot start.")
    else:
        # بناء تطبيق البوت
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # ربط الأوامر بالدوال الخاصة بها
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('help', help_command))
        application.add_handler(CommandHandler('clear', clear_history))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        
        # تشغيل البوت
        logging.info("Cybersecurity Bot is running successfully!")
        application.run_polling()
