# PM Backend - Django
# syntax=docker/dockerfile:1
FROM python:3.12-slim

# 環境変数設定
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PADDLE_PDX_CACHE_HOME=/app/ocr_models

WORKDIR /app

# システム依存パッケージのインストール（mysqlclient用、日本語フォント、AIアプリのOCR）
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    fonts-ipafont-gothic \
    fonts-takao-gothic \
    tesseract-ocr \
    tesseract-ocr-jpn \
    tesseract-ocr-eng

# Python依存パッケージのインストール（pipキャッシュを再利用して高速化）
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
# アプリケーションコードをコピー
COPY . .

# 静的ファイル収集
RUN python manage.py collectstatic --noinput || true

# ポート公開
EXPOSE 8081

# gunicornで起動
CMD ["gunicorn", "--bind", "0.0.0.0:8081", "--workers", "3", "project.wsgi:application"]
