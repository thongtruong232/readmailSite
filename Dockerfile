# Base image phù hợp cho CapRover deploy
FROM python:3.11-slim

# Giữ layer nhỏ và tránh prompt khi apt-get
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=readmailweb.settings \
    REDIS_HOST=redis \
    REDIS_PORT=6379

WORKDIR /app

# Cài gói hệ thống cần cho biên dịch dependencies Python (libpq cho postgres)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt và cài đặt các Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ dự án vào container
COPY . .

# Expose port 8002 cho Daphne
EXPOSE 8002

# Thiết lập biến môi trường
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=readmailweb.settings
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379

# Command để chạy Daphne
CMD ["daphne", "-b", "0.0.0.0", "-p", "8002", "readmailweb.asgi:application"] 