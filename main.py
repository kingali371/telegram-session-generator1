# main.py
import os
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import (
    ApiIdInvalid,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid
)
from contextlib import asynccontextmanager
import logging

# ============ إعدادات التسجيل ============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ قراءة متغيرات البيئة ============
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# التحقق من وجود المتغيرات الأساسية
if not API_ID or not API_HASH:
    logger.error("❌ API_ID و API_HASH مطلوبين في متغيرات البيئة")
if not BOT_TOKEN:
    logger.warning("⚠️ BOT_TOKEN غير موجود - البوت لن يعمل")

# ============ التخزين المؤقت ============
temp_sessions = {}      # للجلسات المؤقتة لاستخراج الحسابات
user_states = {}        # لحالة كل مستخدم في البوت

# ============ دوال استخراج الجلسات ============

async def send_verification_code(phone: str, user_id: int = None):
    """إرسال رمز التحقق إلى رقم الهاتف"""
    try:
        # التحقق من صحة رقم الهاتف
        if not phone.startswith("+") or not phone[1:].isdigit():
            return {
                "success": False,
                "message": "❌ رقم الهاتف غير صحيح. يجب أن يبدأ بـ + متبوعاً بالأرقام فقط"
            }
        
        # إنشاء عميل مؤقت
        temp_client = Client(
            f"temp_{phone}_{id(phone)}",
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True
        )
        
        # الاتصال بخوادم تيليجرام
        await temp_client.connect()
        
        # إرسال رمز التحقق
        result = await temp_client.send_code(phone)
        
        # تخزين بيانات الجلسة المؤقتة
        session_data = {
            "client": temp_client,
            "phone": phone,
            "phone_code_hash": result.phone_code_hash,
            "step": "code_sent"
        }
        
        if user_id:
            temp_sessions[user_id] = session_data
        else:
            temp_sessions[f"phone_{phone}"] = session_data
        
        return {
            "success": True,
            "message": "✅ تم إرسال رمز التحقق إلى هاتفك",
            "phone_code_hash": result.phone_code_hash
        }
        
    except ApiIdInvalid:
        return {"success": False, "message": "❌ خطأ: API ID أو API Hash غير صحيح"}
    except PhoneNumberInvalid:
        return {"success": False, "message": "❌ خطأ: رقم الهاتف غير صحيح أو غير مسجل في تيليجرام"}
    except Exception as e:
        return {"success": False, "message": f"❌ خطأ غير متوقع: {str(e)}"}


async def get_session_string(phone: str, code: str, password: str = None, user_id: int = None):
    """التحقق من رمز التحقق والحصول على الجلسة النصية"""
    try:
        # استرجاع بيانات الجلسة المؤقتة
        session_data = None
        
        if user_id and user_id in temp_sessions:
            session_data = temp_sessions[user_id]
        elif f"phone_{phone}" in temp_sessions:
            session_data = temp_sessions[f"phone_{phone}"]
        
        if not session_data:
            return {
                "success": False,
                "message": "❌ لم يتم العثور على جلسة نشطة. يرجى إعادة إرسال رمز التحقق"
            }
        
        temp_client = session_data["client"]
        phone_code_hash = session_data["phone_code_hash"]
        
        # محاولة تسجيل الدخول
        try:
            await temp_client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            
        except SessionPasswordNeeded:
            if not password:
                return {
                    "success": False,
                    "message": "🔐 هذا الحساب مفعّل بخطوتين (2FA). يرجى إدخال كلمة المرور",
                    "need_password": True
                }
            
            try:
                await temp_client.check_password(password)
            except PasswordHashInvalid:
                return {
                    "success": False,
                    "message": "❌ كلمة المرور غير صحيحة. يرجى المحاولة مرة أخرى",
                    "need_password": True
                }
        
        # تصدير الجلسة النصية
        session_string = await temp_client.export_session_string()
        
        # الحصول على معلومات الحساب
        me = await temp_client.get_me()
        
        # تنظيف الجلسة المؤقتة
        await temp_client.disconnect()
        if user_id and user_id in temp_sessions:
            del temp_sessions[user_id]
        elif f"phone_{phone}" in temp_sessions:
            del temp_sessions[f"phone_{phone}"]
        
        return {
            "success": True,
            "message": "✅ تم استخراج الجلسة بنجاح",
            "session_string": session_string,
            "user_info": {
                "id": me.id,
                "first_name": me.first_name,
                "last_name": me.last_name,
                "username": me.username,
                "phone": me.phone_number
            }
        }
        
    except PhoneCodeInvalid:
        return {"success": False, "message": "❌ رمز التحقق غير صحيح. يرجى المحاولة مرة أخرى"}
    except PhoneCodeExpired:
        return {"success": False, "message": "❌ انتهت صلاحية رمز التحقق. يرجى إعادة إرسال الرمز"}
    except Exception as e:
        return {"success": False, "message": f"❌ خطأ غير متوقع: {str(e)}"}


# ============ إعداد FastAPI مع تشغيل البوت ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """تشغيل البوت عند بدء التطبيق وإيقافه عند الإغلاق"""
    # بدء تشغيل البوت في الخلفية
    bot_task = asyncio.create_task(run_telegram_bot())
    logger.info("🚀 تم بدء تشغيل البوت")
    yield
    # إيقاف البوت عند إغلاق التطبيق
    bot_task.cancel()
    logger.info("🛑 تم إيقاف البوت")

app = FastAPI(lifespan=lifespan)


# ============ بوت تيليجرام ============

async def run_telegram_bot():
    """تشغيل بوت تيليجرام"""
    try:
        bot = Client("telegram_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
        
        @bot.on_message(filters.command("start"))
        async def start_command(client: Client, message: Message):
            await message.reply_text(
                "🌟 **مرحباً بك في بوت استخراج الجلسات!** 🌟\n\n"
                "أرسل `/extract` لبدء استخراج جلسة جديدة\n"
                "أرسل `/help` للمساعدة\n"
                "أرسل `/cancel` لإلغاء العملية\n\n"
                "🔒 **آمن بالكامل** - لا يتم حفظ أي بيانات",
                parse_mode="markdown"
            )
        
        @bot.on_message(filters.command("help"))
        async def help_command(client: Client, message: Message):
            await message.reply_text(
                "📖 **دليل الاستخدام:**\n\n"
                "1️⃣ أرسل `/extract`\n"
                "2️⃣ أدخل رقم هاتفك مع مفتاح الدولة\n"
                "   مثال: `+966512345678`\n"
                "3️⃣ أدخل رمز التحقق من تيليجرام\n"
                "4️⃣ إذا كان الحساب مفعّل بخطوتين، أدخل كلمة المرور\n"
                "5️⃣ احصل على الجلسة النصية\n\n"
                "⚠️ **تنبيه:** لا تشارك الجلسة مع أي شخص!",
                parse_mode="markdown"
            )
        
        @bot.on_message(filters.command("extract"))
        async def extract_command(client: Client, message: Message):
            user_id = message.from_user.id
            user_states[user_id] = {"step": "phone"}
            await message.reply_text(
                "📱 **الخطوة 1/3: أدخل رقم هاتفك**\n\n"
                "مثال: `+966512345678`\n\n"
                "أو أرسل `/cancel` لإلغاء العملية",
                parse_mode="markdown"
            )
        
        @bot.on_message(filters.command("cancel"))
        async def cancel_command(client: Client, message: Message):
            user_id = message.from_user.id
            # تنظيف البيانات
            if user_id in temp_sessions:
                try:
                    await temp_sessions[user_id]["client"].disconnect()
                except:
                    pass
                del temp_sessions[user_id]
            if user_id in user_states:
                del user_states[user_id]
            await message.reply_text("❌ تم إلغاء العملية بنجاح")
        
        @bot.on_message(filters.text & ~filters.command(["start", "help", "extract", "cancel"]))
        async def handle_messages(client: Client, message: Message):
            user_id = message.from_user.id
            text = message.text.strip()
            
            # التحقق من وجود حالة نشطة
            if user_id not in user_states:
                await message.reply_text("❌ لا توجد عملية نشطة. أرسل /extract لبدء جديدة")
                return
            
            step = user_states[user_id]["step"]
            
            if step == "phone":
                # معالجة رقم الهاتف
                result = await send_verification_code(text, user_id)
                
                if result["success"]:
                    user_states[user_id]["step"] = "code"
                    user_states[user_id]["phone"] = text
                    await message.reply_text(
                        "✅ **تم إرسال رمز التحقق!**\n\n"
                        "🔢 **الخطوة 2/3:** أدخل الرمز المكون من 5 أرقام\n"
                        "📱 افحص تطبيق تيليجرام\n\n"
                        "**الرمز:**",
                        parse_mode="markdown"
                    )
                else:
                    await message.reply_text(result["message"])
            
            elif step == "code":
                # معالجة رمز التحقق
                status_msg = await message.reply_text("🔄 جاري التحقق من الرمز...")
                
                phone = user_states[user_id]["phone"]
                result = await get_session_string(phone, text, user_id=user_id)
                
                await status_msg.delete()
                
                if result["success"]:
                    # حفظ كلمة المرور مؤقتاً إذا احتجناها
                    session_string = result["session_string"]
                    user_info = result["user_info"]
                    
                    await message.reply_text(
                        f"🎉 **تم استخراج الجلسة بنجاح!** 🎉\n\n"
                        f"📱 **الحساب:** {user_info['first_name']}\n"
                        f"🆔 **المعرف:** `{user_info['id']}`\n\n"
                        f"🔑 **الجلسة النصية:**\n"
                        f"`{session_string}`\n\n"
                        f"⚠️ **تحذير:** لا تشارك هذه الجلسة مع أي شخص!",
                        parse_mode="markdown"
                    )
                    
                    # تنظيف البيانات
                    if user_id in user_states:
                        del user_states[user_id]
                    
                elif result.get("need_password"):
                    user_states[user_id]["step"] = "password"
                    user_states[user_id]["temp_code"] = text
                    await message.reply_text(
                        "🔐 **الخطوة 3/3: أدخل كلمة المرور**\n\n"
                        "حسابك مفعّل بخطوتين (2FA)\n"
                        "يرجى إدخال كلمة المرور الخاصة بك:",
                        parse_mode="markdown"
                    )
                else:
                    await message.reply_text(result["message"])
            
            elif step == "password":
                # معالجة كلمة المرور
                status_msg = await message.reply_text("🔄 جاري التحقق من كلمة المرور...")
                
                phone = user_states[user_id]["phone"]
                code = user_states[user_id]["temp_code"]
                password = text
                
                result = await get_session_string(phone, code, password=password, user_id=user_id)
                
                await status_msg.delete()
                
                if result["success"]:
                    session_string = result["session_string"]
                    user_info = result["user_info"]
                    
                    await message.reply_text(
                        f"🎉 **تم استخراج الجلسة بنجاح!** 🎉\n\n"
                        f"📱 **الحساب:** {user_info['first_name']}\n"
                        f"🆔 **المعرف:** `{user_info['id']}`\n\n"
                        f"🔑 **الجلسة النصية:**\n"
                        f"`{session_string}`\n\n"
                        f"⚠️ **تحذير:** لا تشارك هذه الجلسة مع أي شخص!",
                        parse_mode="markdown"
                    )
                    
                    # تنظيف البيانات
                    if user_id in user_states:
                        del user_states[user_id]
                else:
                    await message.reply_text(result["message"])
        
        logger.info("✅ بوت تيليجرام جاهز للعمل")
        await bot.start()
        await asyncio.Event().wait()  # انتظار إلى الأبد
        
    except Exception as e:
        logger.error(f"❌ خطأ في البوت: {e}")


# ============ مسارات FastAPI ============

@app.get("/")
async def root():
    """الصفحة الرئيسية"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>بوت استخراج جلسات تيليجرام</title>
        <meta charset="UTF-8">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
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
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            }
            h1 { text-align: center; margin-bottom: 30px; }
            .status {
                text-align: center;
                padding: 10px;
                background: #00c853;
                color: white;
                border-radius: 8px;
                margin: 20px 0;
                font-weight: bold;
            }
            .info {
                background: rgba(0,0,0,0.2);
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }
            code {
                background: rgba(0,0,0,0.3);
                padding: 2px 6px;
                border-radius: 4px;
                font-family: monospace;
            }
            .button {
                display: inline-block;
                background: white;
                color: #764ba2;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 8px;
                margin-top: 20px;
                font-weight: bold;
                transition: transform 0.2s;
            }
            .button:hover {
                transform: scale(1.05);
            }
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            .feature {
                background: rgba(255,255,255,0.1);
                padding: 10px;
                border-radius: 8px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 بوت استخراج جلسات تيليجرام</h1>
            <div class="status">
                ✅ البوت يعمل بنجاح
            </div>
            
            <div class="info">
                <h3>📌 كيفية الاستخدام:</h3>
                <ol>
                    <li>افتح البوت في تطبيق تيليجرام</li>
                    <li>أرسل الأمر <code>/start</code></li>
                    <li>أرسل الأمر <code>/extract</code></li>
                    <li>اتبع التعليمات للحصول على جلسة النص</li>
                </ol>
            </div>
            
            <div class="features">
                <div class="feature">🔒 آمن بالكامل</div>
                <div class="feature">⚡ سريع وسهل</div>
                <div class="feature">📱 يدعم 2FA</div>
                <div class="feature">🗑️ حذف تلقائي للبيانات</div>
            </div>
            
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
        "active_sessions": len(temp_sessions),
        "active_users": len(user_states),
        "api_id_configured": bool(API_ID),
        "bot_token_configured": bool(BOT_TOKEN)
    }

@app.get("/stats")
async def get_stats():
    """إحصائيات البوت"""
    return {
        "active_sessions": len(temp_sessions),
        "active_users": len(user_states),
        "total_interactions": len(user_states) + len(temp_sessions)
    }

# ============ تشغيل التطبيق ============
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
