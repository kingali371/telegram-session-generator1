# main.py
import os
import asyncio
import threading
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# تهيئة تطبيق FastAPI
app = FastAPI(
    title="Telegram Session Generator",
    description="إنشاء جلسات تيليجرام بسهولة",
    version="1.0.0"
)

# متغيرات عامة
session_data = {}
current_status = {"status": "ready", "message": "الخادم جاهز لإنشاء الجلسات"}

# نماذج البيانات
class PhoneRequest(BaseModel):
    phone: str

class CodeRequest(BaseModel):
    phone: str
    code: str
    password: str = None

class SessionResponse(BaseModel):
    success: bool
    session_string: str = None
    message: str

# ============ دوال إنشاء الجلسة ============

async def send_verification_code(phone: str):
    """إرسال رمز التحقق إلى رقم الهاتف"""
    try:
        api_id = int(os.environ.get("API_ID"))
        api_hash = os.environ.get("API_HASH")
        
        # استخدام جلسة مؤقتة
        app_client = Client(":memory:", api_id=api_id, api_hash=api_hash)
        await app_client.connect()
        
        # إرسال رمز التحقق
        result = await app_client.send_code(phone)
        await app_client.disconnect()
        
        # تخزين معلومات الجلسة مؤقتاً
        session_data[phone] = {
            "phone": phone,
            "phone_code_hash": result.phone_code_hash,
            "step": "code_sent"
        }
        
        return {"success": True, "message": "تم إرسال رمز التحقق"}
    except Exception as e:
        logger.error(f"خطأ في إرسال الرمز: {e}")
        return {"success": False, "message": str(e)}

async def verify_code_and_get_session(phone: str, code: str, password: str = None):
    """التحقق من الرمز والحصول على الجلسة"""
    try:
        api_id = int(os.environ.get("API_ID"))
        api_hash = os.environ.get("API_HASH")
        
        app_client = Client(":memory:", api_id=api_id, api_hash=api_hash)
        await app_client.connect()
        
        # الحصول على معلومات الجلسة المخزنة
        session_info = session_data.get(phone, {})
        phone_code_hash = session_info.get("phone_code_hash")
        
        if not phone_code_hash:
            return {"success": False, "message": "لم يتم إرسال رمز التحقق بعد"}
        
        # محاولة تسجيل الدخول
        try:
            await app_client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeeded:
            if password:
                await app_client.check_password(password)
            else:
                await app_client.disconnect()
                return {"success": False, "message": "كلمة المرور مطلوبة (2FA)"}
        
        # تصدير الجلسة النصية
        string_session = await app_client.export_session_string()
        await app_client.disconnect()
        
        # تنظيف البيانات المؤقتة
        del session_data[phone]
        
        return {"success": True, "session_string": string_session, "message": "تم إنشاء الجلسة بنجاح"}
        
    except Exception as e:
        logger.error(f"خطأ في التحقق: {e}")
        return {"success": False, "message": str(e)}

# ============ مسارات API ============

@app.get("/", response_class=HTMLResponse)
async def root():
    """الصفحة الرئيسية - واجهة بسيطة"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>مولد جلسات تيليجرام</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                background: #f0f2f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { color: #1e90ff; text-align: center; }
            input, button {
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
            }
            button {
                background: #1e90ff;
                color: white;
                border: none;
                cursor: pointer;
            }
            button:hover { background: #0066cc; }
            .result {
                margin-top: 20px;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 5px;
                display: none;
            }
            .result.success { background: #d4edda; color: #155724; }
            .result.error { background: #f8d7da; color: #721c24; }
            .session-code {
                font-family: monospace;
                word-break: break-all;
                background: #fff;
                padding: 10px;
                border-radius: 5px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 مولد جلسات تيليجرام</h1>
            
            <div id="step1">
                <h3>الخطوة 1: إرسال رمز التحقق</h3>
                <input type="text" id="phone" placeholder="رقم الهاتف (مثال: +966512345678)" dir="ltr">
                <button onclick="sendCode()">إرسال الرمز</button>
            </div>
            
            <div id="step2" style="display:none;">
                <h3>الخطوة 2: إدخال رمز التحقق</h3>
                <input type="text" id="code" placeholder="رمز التحقق" dir="ltr">
                <input type="password" id="password" placeholder="كلمة المرور (إذا كانت مفعلة)">
                <button onclick="verifyCode()">تسجيل الدخول</button>
            </div>
            
            <div id="result" class="result"></div>
        </div>
        
        <script>
            let currentPhone = '';
            
            async function sendCode() {
                const phone = document.getElementById('phone').value;
                if (!phone) {
                    alert('الرجاء إدخال رقم الهاتف');
                    return;
                }
                currentPhone = phone;
                
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                resultDiv.className = 'result';
                resultDiv.innerHTML = 'جاري إرسال الرمز...';
                
                try {
                    const response = await fetch('/send-code', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({phone: phone})
                    });
                    const data = await response.json();
                    
                    if (data.success) {
                        resultDiv.innerHTML = '✅ ' + data.message;
                        resultDiv.className = 'result success';
                        document.getElementById('step1').style.display = 'none';
                        document.getElementById('step2').style.display = 'block';
                    } else {
                        resultDiv.innerHTML = '❌ ' + data.message;
                        resultDiv.className = 'result error';
                    }
                } catch (error) {
                    resultDiv.innerHTML = '❌ خطأ في الاتصال: ' + error.message;
                    resultDiv.className = 'result error';
                }
            }
            
            async function verifyCode() {
                const code = document.getElementById('code').value;
                const password = document.getElementById('password').value;
                
                if (!code) {
                    alert('الرجاء إدخال رمز التحقق');
                    return;
                }
                
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                resultDiv.className = 'result';
                resultDiv.innerHTML = 'جاري التحقق من الرمز...';
                
                try {
                    const response = await fetch('/verify-code', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            phone: currentPhone,
                            code: code,
                            password: password || null
                        })
                    });
                    const data = await response.json();
                    
                    if (data.success) {
                        resultDiv.innerHTML = `
                            ✅ ${data.message}<br><br>
                            <strong>الجلسة النصية:</strong><br>
                            <div class="session-code">${data.session_string}</div><br>
                            ⚠️ احتفظ بهذه الجلسة ولا تشاركها مع أي شخص!
                        `;
                        resultDiv.className = 'result success';
                    } else {
                        resultDiv.innerHTML = '❌ ' + data.message;
                        resultDiv.className = 'result error';
                    }
                } catch (error) {
                    resultDiv.innerHTML = '❌ خطأ في الاتصال: ' + error.message;
                    resultDiv.className = 'result error';
                }
            }
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """فحص صحة الخادم"""
    return {"status": "healthy", "service": "Telegram Session Generator"}

@app.get("/status")
async def get_status():
    """الحصول على حالة الخادم"""
    return current_status

@app.post("/send-code")
async def send_code(request: PhoneRequest):
    """API: إرسال رمز التحقق"""
    result = await send_verification_code(request.phone)
    return result

@app.post("/verify-code")
async def verify_code(request: CodeRequest):
    """API: التحقق من الرمز والحصول على الجلسة"""
    result = await verify_code_and_get_session(request.phone, request.code, request.password)
    return result

# ============ تشغيل التطبيق ============

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
