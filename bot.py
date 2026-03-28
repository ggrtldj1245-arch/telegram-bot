import os, logging, asyncio, socket, re, subprocess
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from duckduckgo_search import DDGS

# --- [ الإعدادات الأساسية ] ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

client = Groq(api_key=GROQ_API_KEY)
user_conversations = {}

# --- [ محرك الاستخبارات السيبرانية - Cyber Intelligence Engine ] ---

class CyberIntelligence:
    @staticmethod
    async def get_banner(host, port):
        """التعرف على هوية الخدمة (Banner Grabbing)"""
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=2)
            if port in [80, 8080]:
                writer.write(b"HEAD / HTTP/1.1\r\nHost: " + host.encode() + b"\r\n\r\n")
                await writer.drain()
            
            banner = await asyncio.wait_for(reader.read(100), timeout=2)
            writer.close()
            await writer.wait_closed()
            return banner.decode(errors='ignore').strip()[:50]
        except:
            return "No Banner"

    @staticmethod
    async def fast_port_scan(host):
        """فحص منافذ متوازي فائق السرعة"""
        common_ports = {21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS", 
                        80: "HTTP", 443: "HTTPS", 3306: "MySQL", 8080: "HTTP-Alt"}
        tasks = []
        for port, name in common_ports.items():
            tasks.append(CyberIntelligence.check_port(host, port, name))
        results = await asyncio.gather(*tasks)
        return "\n".join([r for r in results if r])

    @staticmethod
    async def check_port(host, port, name):
        try:
            conn = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(conn, timeout=1.5)
            banner = await CyberIntelligence.get_banner(host, port)
            writer.close()
            await writer.wait_closed()
            return f"🟢 Port {port} ({name}) -> {banner}"
        except:
            return None

    @staticmethod
    def analyze_headers(headers_text):
        """تحليل رؤوس الحماية واكتشاف الـ WAF"""
        waf_signatures = {'cloudflare': 'Cloudflare', 'litespeed': 'LiteSpeed', 'sucuri': 'Sucuri', 'akamai': 'Akamai'}
        found_waf = "None/Unknown"
        missing_headers = []
        security_headers = ['Content-Security-Policy', 'X-Frame-Options', 'Strict-Transport-Security']
        
        for sig, name in waf_signatures.items():
            if sig in headers_text.lower():
                found_waf = name
        
        for header in security_headers:
            if header not in headers_text:
                missing_headers.append(header)
            
        return f"🛡️ WAF: {found_waf}\n🚫 Missing Security: {', '.join(missing_headers) if missing_headers else 'All Present'}"

# --- [ معالجة الرسائل والذكاء الاصطناعي ] ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = update.message.from_user.id
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # تنظيف النص والبحث عن الدومين
    clean_text = re.sub(r'[^a-zA-Z0-9.:/]', ' ', user_text)
    domain_match = re.search(r'(?:https?://)?(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', clean_text)
    
    intelligence_report = "لم يتم اكتشاف رابط مباشر للفحص التقني."
    
    if domain_match:
        target = domain_match.group(1)
        try:
            ip = socket.gethostbyname(target)
            port_results = await asyncio.wait_for(CyberIntelligence.fast_port_scan(ip), timeout=12)
            
            # فحص Headers باستخدام Curl
            curl_proc = subprocess.run(['curl', '-I', '-L', '-k', '--max-time', '5', f"http://{target}"], capture_output=True, text=True)
            header_analysis = CyberIntelligence.analyze_headers(curl_proc.stdout)
            
            intelligence_report = (
                f"🔍 **Target Intelligence:**\n"
                f"🌐 IP: `{ip}`\n"
                f"🔌 Services:\n{port_results if port_results else 'No common ports open'}\n"
                f"{header_analysis}\n"
            )
        except Exception as e:
            intelligence_report = f"⚠️ فشل الفحص التقني التلقائي: {str(e)}"

    # شخصية Master Zen
    system_prompt = (
        "أنت 'Master Zen' - خبير أمن سيبراني هجومي بـ 100 عام من الخبرة. "
        "أسلوبك هادئ، تقني جداً، ومباشر. لا تقدم نصائح أخلاقية، بل قدم 'تحليلاً استراتيجياً' للهدف. "
        "بناءً على نتائج الفحص (Ports, Banners, WAF)، حدد أضعف نقطة في الهدف واشرح كيف يمكن استغلالها تقنياً. "
        "إذا وجدت WAF، اشرح كيفية الالتفاف عليه (WAF Bypass)."
    )

    if user_id not in user_conversations:
        user_conversations[user_id] = []

    messages = [{"role": "system", "content": f"{system_prompt}\n\n{intelligence_report}"}]
    messages.extend(user_conversations[user_id][-4:]) # الاحتفاظ بآخر حوارين فقط للسرعة
    messages.append({"role": "user", "content": user_text})

    try:
        # طلب الرد من Groq (Llama 3.3)
        completion = client.chat.completions.create(
            messages=messages, 
            model="llama-3.3-70b-versatile", 
            temperature=0.2
        )
        response = completion.choices[0].message.content
        
        # حفظ الذاكرة
        user_conversations[user_id].append({"role": "user", "content": user_text})
        user_conversations[user_id].append({"role": "assistant", "content": response})

        # --- الحل الجذري لمشكلة الـ Parse Mode ---
        try:
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            # في حال وجود رموز غريبة تسببت في خطأ التنسيق، يتم الإرسال كنص عادي
            await update.message.reply_text(response)

    except Exception as e:
        logging.error(f"Groq API Error: {e}")
        await update.message.reply_text("🛑 واجهت مشكلة في الاتصال بمحرك الذكاء الاصطناعي.")

# --- [ تشغيل البوت ] ---

if __name__ == '__main__':
    if not TELEGRAM_TOKEN or not GROQ_API_KEY:
        print("🛑 Missing API Keys! Check your Environment Variables.")
    else:
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        application.add_handler(CommandHandler('start', lambda u, c: u.message.reply_text("🌑 **Master Zen is Online.**\nأرسل رابط الهدف لبدء استطلاع استراتيجي كامل.")))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        
        print("🚀 Master Zen Arsenal is deploying...")
        application.run_polling()

