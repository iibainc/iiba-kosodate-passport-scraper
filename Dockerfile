# ベースイメージ
FROM python:3.11-slim

WORKDIR /app

# 依存関係をインストール（システム全体）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY src/ ./src/
COPY .env.example .env

# アプリケーションユーザーを作成
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# 環境変数を設定
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Cloud Run用のHTTPサーバーを起動
CMD ["python", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8080"]
