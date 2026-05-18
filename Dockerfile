FROM python:3.11-slim

WORKDIR /app

# نسخ ملف المتطلبات أولاً للاستفادة من التخزين المؤقت
COPY requirements.txt .

# تثبيت المتطلبات مع تجنب تثبيت pydantic-core من المصدر
RUN pip install --no-cache-dir --no-binary pydantic-core pydantic

# نسخ باقي ملفات المشروع
COPY . .

# المنفذ الذي سيستخدمه Render
ENV PORT=8000

# أمر تشغيل التطبيق
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
