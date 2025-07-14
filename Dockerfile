# استخدام صورة أساسية خفيفة الوزن
FROM python:3.9-slim

# تعيين دليل العمل
WORKDIR /app

# نسخ ملفات المشروع
COPY . .

# تثبيت التبعيات
RUN pip install --no-cache-dir -r requirements.txt

# تعيين المنفذ الذي سيتم تعريضه
EXPOSE 10000

# تشغيل البوت عند بدء الحاوية
CMD ["python", "tast3.py"]
