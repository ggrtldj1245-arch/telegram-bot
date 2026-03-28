import os, logging, asyncio, socket, re, requests
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# إعدادات
logging.basicConfig(level=logging.INFO)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
client = Groq(api_key=GROQ_API_KEY)

class ProScanner:
    @staticmethod
    async def scan_target(domain):
        report = {"ip": "Unknown", "ports": [], "headers": {}, "waf": "Unknown"}
        try:
            # 1. جلب الـ IP
            report["ip"] = socket.gethostbyname(domain)
            
            # 2. فحص المنافذ (الأساسية فقط للسرعة)
            for port in [80, 443, 22, 21, 3306]:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                if sock.connect_ex((report["ip"], port)) == 0:
                    report["ports"].append(port)
                sock.close()

            # 3. جلب الـ Headers (بديل Curl)
            url = f"https://{domain}" if report["ports"] and 443 in report["ports"] else f"http://{domain}"
            response = requests.get(url, timeout=5, verify=False, headers={'User-Agent': 'Mozilla/5.0'})
            report["headers"] = dict(response.headers)
            
            # 4. كشف الـ WAF
            server = report["headers"].get("Server", "").lower()
            if "cloudflare" in server: report["waf"] = "Cloudflare"
            elif "litespeed" in server: report["waf"] = "LiteSpeed"
            else: report["waf"] = "Not Detected / Hidden"
            
        except Exception as e:
            logging.error(f"Scan failed: {e}")
        return report

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = update.message.from_user.id
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    domain_match = re.search(r'(?:https?://)?(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', user_text)
    
    scan_data = None
    if domain_match:
        target = domain_match.group(1)
        scan_data = await ProScanner.scan_target(target)

    # الـ Prompt الصارم لمنع التحليل النظري
    system_prompt = (
        "أنت Master Zen. إذا كانت بيانات الفحص المرفقة فارغة أو 'Unknown'، "
        "أخبر المستخدم فوراً أنك فشلت في الوصول للهدف تقنياً ولا تقدم أي تحليل نظري عام. "
        "أما إذا وجدت بيانات، فقدم تحليلاً هجومياً بناءً على الأرقام والإصدارات المذكورة فقط."
    )

    data_to_ai = f"TARGET DATA:\n{scan_data}" if scan_data else "NO SCAN DATA AVAILABLE."
    
    messages = [{"role": "system", "content": f"{system_prompt}\n\n{data_to_ai}"},
                {"role": "user", "content": user_text}]

    try:
        completion = client.chat.completions.create(messages=messages, model="llama-3.3-70b-versatile", temperature=0.1)
        response = completion.choices[0].message.content
        
        try:
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        except:
            await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"🛑 Error: {e}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()


