import os
import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Bot is running"}

if __name__ == "__main__":
    # قراءة المنفذ من متغيرات البيئة (Render يضيفه تلقائياً)
    port = int(os.environ.get("PORT", 8000))
    
    # تشغيل الخادم على 0.0.0.0 للاستماع لجميع الاتصالات
    uvicorn.run(app, host="0.0.0.0", port=port)
