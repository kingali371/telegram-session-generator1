from pyrogram import Client

def main():
    api_id = int(input("أدخل معرف API: "))
    api_hash = input("أدخل مفتاح API: ")
    phone = input("أدخل رقم الهاتف (مع مفتاح الدولة): ")
    
    app = Client("my_session", api_id=api_id, api_hash=api_hash)
    
    async def run():
        async with app:
            await app.send_code(phone)
            code = input("أدخل رمز التحقق: ")
            await app.sign_in(phone, code)
            print("✅ تم إنشاء الجلسة بنجاح!")
    
    app.run(run())

if __name__ == "__main__":
    main()
