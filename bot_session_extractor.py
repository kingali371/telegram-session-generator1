# bot_session_extractor.py
import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from dotenv import load_dotenv
import json

load_dotenv()

# إعدادات البوت
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# قاموس لتخزين بيانات المستخدمين المؤقتة
user_data = {}

# إنشاء البوت
bot = Client("session_extractor_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ============ دوال مساعدة ============

async def create_keyboard(buttons):
    """إنشاء لوحة مفاتيح مخصصة"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(btn) for btn in row] for row in buttons],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

async def safe_delete_message(message: Message, delay: int = 0):
    """حذف رسالة بأمان"""
    try:
        await asyncio.sleep(delay)
        await message.delete()
    except:
        pass

# ============ أوامر البوت ============

@bot.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """رسالة الترحيب"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    welcome_text = f"""
🌟 **مرحباً بك {user_name}!** 🌟

أنا بوت استخراج جلسات تيليجرام.

📌 **ما هي الجلسة؟**
الجلسة النصية (String Session) تسمح لك بتسجيل الدخول إلى حسابك بدون الحاجة إلى إدخال رقم الهاتف ورمز التحقق في كل مرة.

🔧 **كيفية الاستخدام:**
1️⃣ أرسل `/extract` لبدء استخراج جلسة جديدة
2️⃣ أدخل رقم هاتفك مع مفتاح الدولة
3️⃣ أدخل رمز التحقق الذي سيصلك
4️⃣ احصل على الجلسة النصية

⚠️ **تنبيهات أمنية:**
• لا تشارك الجلسة مع أي شخص
• سيتم حذف بياناتك فوراً بعد الاستخراج
• البوت لا يحفظ أي معلومات شخصية

💡 **الأوامر المتاحة:**
/extract - استخراج جلسة جديدة
/cancel - إلغاء العملية
/help - المساعدة
/about - عن البوت
    """
    
    await message.reply(welcome_text, parse_mode=ParseMode.MARKDOWN)
    
    # إرسال لوحة مفاتيح رئيسية
    keyboard = await create_keyboard([
        ["📱 استخراج جلسة جديدة"],
        ["ℹ️ المساعدة", "❌ إلغاء"]
    ])
    await message.reply("اختر أحد الخيارات:", reply_markup=keyboard)

@bot.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    """رسالة المساعدة"""
    help_text = """
📖 **دليل المساعدة**

**الخطوات بالتفصيل:**

1️⃣ **أرسل** `/extract` لبدء العملية

2️⃣ **أدخل رقم هاتفك** بالصيغة الدولية:
• السعودية: `+966512345678`
• مصر: `+201234567890`
• الإمارات: `+971501234567`

3️⃣ **انتظر رمز التحقق** من تيليجرام

4️⃣ **أدخل الرمز** (6 أرقام)

5️⃣ **إذا كان الحساب مفعّلاً بخطوتين** أدخل كلمة المرور

6️⃣ **ستحصل على الجلسة النصية** احتفظ بها جيداً!

**الأوامر:**
• `/start` - بدء البوت
• `/extract` - استخراج جلسة
• `/cancel` - إلغاء العملية الجارية
• `/help` - هذه الرسالة
• `/about` - معلومات عن البوت

**ملاحظة:** سيتم حذف جميع محادثاتك بعد الانتهاء مباشرة للحفاظ على خصوصيتك.
    """
    await message.reply(help_text, parse_mode=ParseMode.MARKDOWN)

@bot.on_message(filters.command("about"))
async def about_command(client: Client, message: Message):
    """معلومات عن البوت"""
    about_text = """
🤖 **عن البوت**

**الاسم:** Session Extractor Bot
**الإصدار:** 2.0.0
**المكتبة:** Pyrogram

**المميزات:**
✅ استخراج جلسات نصية آمنة
✅ دعم التوثيق بخطوتين (2FA)
✅ حذف تلقائي للبيانات الحساسة
✅ واجهة سهلة الاستخدام

**الخصوصية:**
• لا يتم تخزين أي بيانات
• حذف فوري للمعلومات بعد الاستخراج
• تشفير الاتصال مع تيليجرام

**الدعم:** @BotSupport

⚡ **للاستخدام:** أرسل `/extract`
    """
    await message.reply(about_text, parse_mode=ParseMode.MARKDOWN)

@bot.on_message(filters.command("extract"))
async def extract_command(client: Client, message: Message):
    """بدء عملية استخراج الجلسة"""
    user_id = message.from_user.id
    
    # إعادة تعيين بيانات المستخدم
    user_data[user_id] = {
        "step": "waiting_phone",
        "phone": None,
        "phone_code_hash": None,
        "temp_client": None
    }
    
    # طلب رقم الهاتف
    keyboard = await create_keyboard([["❌ إلغاء"]])
    
    await message.reply(
        "📱 **الخطوة 1/3: أدخل رقم هاتفك**\n\n"
        "أدخل رقم هاتفك مع مفتاح الدولة:\n"
        "• `+966512345678` للأرقام السعودية\n"
        "• `+201234567890` للأرقام المصرية\n\n"
        "**مثال:** +966512345678\n\n"
        "⚠️ سيتم إرسال رمز التحقق إلى هذا الرقم",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

@bot.on_message(filters.command("cancel"))
async def cancel_command(client: Client, message: Message):
    """إلغاء العملية الجارية"""
    user_id = message.from_user.id
    
    if user_id in user_data:
        # تنظيف العميل المؤقت إذا وجد
        if user_data[user_id].get("temp_client"):
            try:
                await user_data[user_id]["temp_client"].disconnect()
            except:
                pass
        del user_data[user_id]
    
    await message.reply(
        "❌ **تم إلغاء العملية بنجاح**\n\n"
        "يمكنك البدء من جديد عبر إرسال `/extract`",
        parse_mode=ParseMode.MARKDOWN
    )

@bot.on_message(filters.text & ~filters.command(["start", "help", "extract", "cancel", "about"]))
async def handle_messages(client: Client, message: Message):
    """معالجة رسائل المستخدمين"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # التعامل مع أزرار لوحة المفاتيح
    if text == "📱 استخراج جلسة جديدة":
        await extract_command(client, message)
        return
    elif text == "ℹ️ المساعدة":
        await help_command(client, message)
        return
    elif text == "❌ إلغاء":
        await cancel_command(client, message)
        return
    
    # إذا لم يكن المستخدم في عملية استخراج
    if user_id not in user_data:
        await message.reply(
            "⚠️ **لا توجد عملية نشطة**\n\n"
            "لبدء استخراج جلسة جديدة، أرسل `/extract`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    step = user_data[user_id]["step"]
    
    if step == "waiting_phone":
        await handle_phone_input(client, message, user_id, text)
    
    elif step == "waiting_code":
        await handle_code_input(client, message, user_id, text)
    
    elif step == "waiting_password":
        await handle_password_input(client, message, user_id, text)

# ============ دوال المعالجة الرئيسية ============

async def handle_phone_input(client: Client, message: Message, user_id: int, phone: str):
    """معالجة رقم الهاتف وإرسال رمز التحقق"""
    # التحقق من صيغة رقم الهاتف
    if not phone.startswith("+") or not phone[1:].isdigit():
        await message.reply(
            "❌ **خطأ في صيغة رقم الهاتف**\n\n"
            "يجب أن يبدأ الرقم بـ `+` متبوعاً برقم الهاتف\n"
            "مثال صحيح: `+966512345678`\n\n"
            "📱 **حاول مرة أخرى:**",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        # إعلام المستخدم
        status_msg = await message.reply(
            "⏳ **جاري الاتصال بخوادم تيليجرام...**\n"
            f"📱 الرقم: `{phone}`\n\n"
            "🔄 سيصلك رمز التحقق خلال ثوانٍ...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # إنشاء عميل مؤقت لهذا المستخدم
        temp_client = Client(
            f"temp_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True
        )
        
        await temp_client.connect()
        
        # إرسال رمز التحقق
        result = await temp_client.send_code(phone)
        
        # تخزين البيانات
        user_data[user_id]["phone"] = phone
        user_data[user_id]["phone_code_hash"] = result.phone_code_hash
        user_data[user_id]["temp_client"] = temp_client
        user_data[user_id]["step"] = "waiting_code"
        
        await status_msg.delete()
        
        # طلب رمز التحقق
        keyboard = await create_keyboard([["❌ إلغاء"]])
        await message.reply(
            "✅ **تم إرسال رمز التحقق!**\n\n"
            "🔢 **الخطوة 2/3: أدخل رمز التحقق**\n\n"
            "• افحص تطبيق تيليجرام\n"
            "• ستصلك رسالة بالرمز\n"
            "• أدخل الرقم المكون من 5-6 أرقام\n\n"
            "**الرمز:**",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        
    except Exception as e:
        await message.reply(
            f"❌ **خطأ في إرسال الرمز**\n\n"
            f"السبب: `{str(e)}`\n\n"
            "💡 تأكد من:\n"
            "• صحة رقم الهاتف\n"
            "• وجود اتصال بالإنترنت\n"
            "• استخدام رقم صحيح مع مفتاح الدولة\n\n"
            "يمكنك المحاولة مرة أخرى بـ `/extract`",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_code_input(client: Client, message: Message, user_id: int, code: str):
    """معالجة رمز التحقق وتسجيل الدخول"""
    
    if not code.isdigit():
        await message.reply(
            "❌ **الرمز يجب أن يحتوي على أرقام فقط!**\n\n"
            "🔢 **حاول مرة أخرى:**"
        )
        return
    
    try:
        status_msg = await message.reply(
            "⏳ **جاري التحقق من الرمز...**\n"
            "🔄 يرجى الانتظار...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        temp_client = user_data[user_id]["temp_client"]
        phone = user_data[user_id]["phone"]
        phone_code_hash = user_data[user_id]["phone_code_hash"]
        
        # محاولة تسجيل الدخول
        try:
            await temp_client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            
            # تسجيل الدخول ناجح بدون كلمة مرور
            session_string = await temp_client.export_session_string()
            
            await status_msg.delete()
            
            # إرسال الجلسة للمستخدم
            await send_session_to_user(message, session_string, phone)
            
            # تنظيف البيانات
            await cleanup_user_data(user_id)
            
        except Exception as e:
            error_msg = str(e)
            
            if "PASSWORD_HASH" in error_msg or "SESSION_PASSWORD_NEEDED" in error_msg:
                # الحساب مفعل بخطوتين
                user_data[user_id]["step"] = "waiting_password"
                await status_msg.delete()
                
                keyboard = await create_keyboard([["❌ إلغاء"]])
                await message.reply(
                    "🔐 **الخطوة 3/3: أدخل كلمة المرور**\n\n"
                    "حسابك مفعّل بخطوتين (2FA)\n"
                    "الرجاء إدخال كلمة المرور الخاصة بك:\n\n"
                    "**كلمة المرور:**",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
            else:
                await status_msg.delete()
                await message.reply(
                    f"❌ **رمز غير صحيح!**\n\n"
                    f"السبب: `{error_msg}`\n\n"
                    "🔢 **حاول مرة أخرى:**\n"
                    "أدخل الرمز الصحيح المكون من 5-6 أرقام",
                    parse_mode=ParseMode.MARKDOWN
                )
                
    except Exception as e:
        await message.reply(
            f"❌ **خطأ غير متوقع**\n\n"
            f"`{str(e)}`\n\n"
            "يمكنك المحاولة مرة أخرى بـ `/extract`",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_password_input(client: Client, message: Message, user_id: int, password: str):
    """معالجة كلمة المرور للحسابات المفعلة بخطوتين"""
    
    try:
        status_msg = await message.reply(
            "⏳ **جاري التحقق من كلمة المرور...**",
            parse_mode=ParseMode.MARKDOWN
        )
        
        temp_client = user_data[user_id]["temp_client"]
        phone = user_data[user_id]["phone"]
        
        # التحقق من كلمة المرور
        await temp_client.check_password(password)
        
        # الحصول على الجلسة
        session_string = await temp_client.export_session_string()
        
        await status_msg.delete()
        
        # إرسال الجلسة
        await send_session_to_user(message, session_string, phone)
        
        # تنظيف البيانات
        await cleanup_user_data(user_id)
        
    except Exception as e:
        await message.reply(
            f"❌ **كلمة المرور غير صحيحة!**\n\n"
            f"السبب: `{str(e)}`\n\n"
            "🔐 **حاول مرة أخرى:**\n"
            "أدخل كلمة المرور الصحيحة",
            parse_mode=ParseMode.MARKDOWN
        )

async def send_session_to_user(message: Message, session_string: str, phone: str):
    """إرسال الجلسة النصية للمستخدم بشكل آمن"""
    
    # إخفاء جزء من رقم الهاتف للخصوصية
    hidden_phone = phone[:5] + "****" + phone[-3:] if len(phone) > 8 else phone
    
    session_text = f"""
🎉 **تم استخراج الجلسة بنجاح!** 🎉

📱 **رقم الهاتف:** `{hidden_phone}`

🔑 **الجلسة النصية (String Session):**
