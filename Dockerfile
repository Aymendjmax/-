# استخدام صورة أساسية خفيفة الوزن
FROM python:3.9-slim

# تعيين دليل العمل
WORKDIR /app

# تثبيت التبعيات النظامية اللازمة
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# نسخ ملفات المشروع
COPY . .

# تثبيت تبعيات بايثون
RUN pip install --no-cache-dir -r requirements.txt

# تشغيل البوت عند بدء الحاوية
CMD ["python", "tast3.py"]
