# 베이스 이미지
FROM python:3.11-slim

# 파이썬 출력 버퍼링 해제
ENV PYTHONUNBUFFERED=1

# 작업 디렉토리 설정
WORKDIR /app

# OS 패키지 설치: Chromium, ChromeDriver, 기타 필수 패키지
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    curl \
    unzip \
    build-essential \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    default-jdk \
    && rm -rf /var/lib/apt/lists/*

# 환경변수로 Chromium/ChromeDriver 경로 지정
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/bin/chromedriver

# Python 패키지 설치
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# 소스코드 복사
COPY . /app/

# 포트 설정
EXPOSE 8000

# Django 서버 실행
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
