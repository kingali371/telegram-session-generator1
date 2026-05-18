import os
import asyncio
from pyrogram import Client
from dotenv import load_dotenv

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

async def main():
    # قراءة المتغيرات
    api_id = int(os.getenv("API_ID"))
    api_hash = os.getenv("API_HASH")
    phone = os.getenv("PHONE_NUMBER")
    
    # التحقق من وجود المتغيرات
    if not all([api_id, api_hash, phone]):
        print("❌ خطأ: تأكد من وجود API_ID, API_HASH, PHONE_NUMBER")
        return
    
    # إنشاء الجلسة
    app = Client("my_session", api_id=api_id, api_hash=api_hash)
    
    async with app:
        try:
            await app.send_code(phone)
            code = input("أدخل رمز التحقق: ")
            await app.sign_in(phone, code)
            
            # الحصول على الجلسة النصية
            string_session = await app.export_session_string()
            print("\n✅ تم إنشاء الجلسة بنجاح!")
            print(f"\n{string_session}\n")
            
            # حفظ الجلسة في ملف
            with open("session.txt", "w") as f:
                f.write(string_session)
            print("💾 تم حفظ الجلسة في session.txt")
            
        except Exception as e:
            print(f"❌ خطأ: {e}")

if __name__ == "__main__":
    asyncio.run(main())
