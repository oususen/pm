# PM Backend - Django
FROM python:3.12-slim

# 環境変数設定
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# システム依存パッケージのインストール（mysqlclient用、日本語フォント）
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    fonts-ipafont-gothic \
    fonts-takao-gothic \
    && rm -rf /var/lib/apt/lists/*

# Python依存パッケージのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# 静的ファイル収集
RUN python manage.py collectstatic --noinput || true

# ポート公開
EXPOSE 8081

# gunicornで起動
CMD ["gunicorn", "--bind", "0.0.0.0:8081", "--workers", "3", "project.wsgi:application"]
