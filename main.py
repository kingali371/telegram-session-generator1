# main.py
import os
import asyncio
import threading
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from contextlib import asynccontextmanager

# ============ إعدادات البوت ============
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# تخزين بيانات المستخدمين المؤقتة
user_sessions = {}

# ============ إعداد FastAPI ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """تشغيل البوت عند بدء التطبيق"""
    # بدء تشغيل البوت في الخلفية
    task = asyncio.create_task(run_bot())
    yield
    # إيقاف البوت عند إغلاق التطبيق
    task.cancel()

app = FastAPI(lifespan=lifespan)

# ============ دوال البوت ============
async def run_bot():
    """تشغيل بوت تيليجرام"""
    try:
        bot = Client("telegram_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
        
        @bot.on_message(filters.command("start"))
        async def start_command(client: Client, message: Message):
            await message.reply_text(
                "🌟 **مرحباً بك في بوت استخراج الجلسات!** 🌟\n\n"
                "للاستخدام، أرسل الأمر `/extract`\n"
                "للمساعدة، أرسل `/help`",
                parse_mode="markdown"
            )
        
        @bot.on_message(filters.command("help"))
        async def help_command(client: Client, message: Message):
            await message.reply_text(
                "📖 **دليل الاستخدام:**\n\n"
                "1️⃣ أرسل `/extract`\n"
                "2️⃣ أدخل رقم هاتفك مع مفتاح الدولة\n"
                "3️⃣ أدخل رمز التحقق\n"
                "4️⃣ احصل على الجلسة النصية",
                parse_mode="markdown"
            )
        
        @bot.on_message(filters.command("extract"))
        async def extract_command(client: Client, message: Message):
            user_id = message.from_user.id
            user_sessions[user_id] = {"step": "phone"}
            await message.reply_text(
                "📱 **الخطوة 1:** أرسل رقم هاتفك\n"
                "مثال: `+966512345678`",
                parse_mode="markdown"
            )
        
        @bot.on_message(filters.text & ~filters.command(["start", "help", "extract"]))
        async def handle_messages(client: Client, message: Message):
            user_id = message.from_user.id
            text = message.text.strip()
            
            if user_id not in user_sessions:
                await message.reply_text("أرسل `/extract` لبدء استخراج جلسة جديدة")
                return
            
            step = user_sessions[user_id]["step"]
            
            if step == "phone":
                # معالجة رقم الهاتف
                if not text.startswith("+") or not text[1:].isdigit():
                    await message.reply_text("❌ رقم غير صحيح! أرسل رقمًا بصيغة `+966512345678`")
                    return
                
                user_sessions[user_id]["phone"] = text
                user_sessions[user_id]["step"] = "waiting_for_code"
                
                # هنا ستضيف كود إرسال رمز التحقق
                await message.reply_text(
                    "✅ **تم استلام رقم الهاتف**\n\n"
                    "🔢 **الخطوة 2:** أدخل رمز التحقق الذي وصل إليك",
                    parse_mode="markdown"
                )
                
            elif step == "waiting_for_code":
                # معالجة رمز التحقق
                if not text.isdigit():
                    await message.reply_text("❌ الرقم يجب أن يحتوي على أرقام فقط!")
                    return
                
                await message.reply_text(
                    "🔄 جاري التحقق من الرمز...\n"
                    "هذه نسخة تجريبية، سيتم إضافة كامل الوظائف قريباً"
                )
                
                # تنظيف الجلسة
                del user_sessions[user_id]
        
        print("🚀 بوت تيليجرام يعمل...")
        await bot.start()
        await asyncio.Event().wait()  # انتظار indefinitely
        
    except Exception as e:
        print(f"❌ خطأ في البوت: {e}")

# ============ مسارات FastAPI ============
@app.get("/")
async def root():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>بوت استخراج الجلسات</title>
        <meta charset="UTF-8">
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                background: rgba(255,255,255,0.1);
                padding: 30px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
            }
            h1 { text-align: center; }
            .status {
                text-align: center;
                padding: 10px;
                background: #00ff00;
                color: #000;
                border-radius: 5px;
                margin: 20px 0;
            }
            code {
                background: #000;
                padding: 2px 5px;
                border-radius: 3px;
            }
            .button {
                display: inline-block;
                background: #fff;
                color: #764ba2;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 5px;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 بوت استخراج جلسات تيليجرام</h1>
            <div class="status">
                ✅ البوت يعمل بنجاح
            </div>
            <p>استخدم البوت عبر تيليجرام:</p>
            <ul>
                <li>🔹 ابحث عن البوت في تيليجرام</li>
                <li>🔹 أرسل <code>/start</code> لبدء الاستخدام</li>
                <li>🔹 أرسل <code>/extract</code> لاستخراج جلسة جديدة</li>
            </ul>
            <center>
                <a href="https://t.me/YourBotUsername" class="button">📱 افتح البوت في تيليجرام</a>
            </center>
        </div>
    </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    """فحص صحة التطبيق"""
    return {
        "status": "healthy",
        "bot_running": True,
        "active_sessions": len(user_sessions)
    }

@app.get("/stats")
async def get_stats():
    """إحصائيات البوت"""
    return {
        "active_sessions": len(user_sessions),
        "total_users": len(user_sessions),
        "status": "running"
    }

# ============ تشغيل التطبيق ============
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
