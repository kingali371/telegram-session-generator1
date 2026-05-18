# main.py
from pyrogram import Client
from fastapi import FastAPI
import threading
import os
import asyncio

# 1. تهيئة تطبيق الويب (لإبقاء Render سعيداً)
app = FastAPI()

# 2. إعدادات الحساب (من الأفضل استخدام متغيرات البيئة)
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
PHONE = os.environ.get("PHONE_NUMBER", "")

# 3. دالة إنشاء الجلسة
async def generate_session():
    # نستخدم ":memory:" لإنشاء جلسة نصية بدلاً من ملف
    async with Client(":memory:", api_id=API_ID, api_hash=API_HASH) as client:
        # إرسال طلب الكود
        await client.send_code(PHONE)
        code = input("❗ لم يتم العثور على جلسة. أدخل رمز التحقق الذي وصل إلى تيليجرام: ")
        
        try:
            await client.sign_in(PHONE, code)
            string_session = await client.export_session_string()
            print(f"\n✅ تم بنجاح! هذه هي جلسة النص الخاصة بك:\n\n{string_session}\n")
            print("⚠️ احتفظ بهذه الجلسة ولا تشاركها مع أي شخص.")
            # يمكنك إرسالها لنفسك عبر البوت أو حفظها
        except Exception as e:
            print(f"❌ فشل تسجيل الدخول: {e}")

# 4. دالة تشغيل Pyrogram في الخلفية
def run_pyrogram():
    asyncio.run(generate_session())

# 5. نقطة الدخول الأساسية لـ Render
@app.get("/")
def read_root():
    return {"message": "Bot is running! Check the logs on Render."}

@app.on_event("startup")
async def startup_event():
    # عند تشغيل السيرفر، ابدأ عملية إنشاء الجلسة في Thread منفصل
    thread = threading.Thread(target=run_pyrogram)
    thread.start()
