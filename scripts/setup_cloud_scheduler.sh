#!/bin/bash
set -e

# Cloud Schedulerセットアップスクリプト
# 複数回実行方式: 15分おきに3回実行して全データを確実に取得

PROJECT_ID=${1:-iiba-staging}
REGION="asia-northeast1"

# 色付きログ
info() { echo -e "\033[0;32m[INFO]\033[0m $1"; }
warn() { echo -e "\033[0;33m[WARN]\033[0m $1"; }
error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; exit 1; }

info "=========================================="
info "Cloud Scheduler セットアップ"
info "=========================================="
info "Project: $PROJECT_ID"
info "Region: $REGION"
info ""

# Cloud Run サービスURLを取得
info "Retrieving Cloud Run service URL..."
SERVICE_URL=$(gcloud run services describe iiba-kosodate-passport-scraper \
    --region $REGION \
    --project $PROJECT_ID \
    --format='value(status.url)' 2>/dev/null)

if [ -z "$SERVICE_URL" ]; then
    error "Cloud Run service not found. Please deploy the service first."
fi

info "Service URL: $SERVICE_URL"
info ""

# サービスアカウント
SA_EMAIL="kosodate-scraper-sa@${PROJECT_ID}.iam.gserviceaccount.com"

info "Creating Cloud Scheduler jobs for Ibaraki (茨城県)..."
info ""

# 既存のジョブを削除（エラーは無視）
info "Cleaning up existing jobs (if any)..."
gcloud scheduler jobs delete kosodate-scrape-ibaraki-run1 \
    --location=$REGION \
    --project=$PROJECT_ID \
    --quiet 2>/dev/null || true

gcloud scheduler jobs delete kosodate-scrape-ibaraki-run2 \
    --location=$REGION \
    --project=$PROJECT_ID \
    --quiet 2>/dev/null || true

gcloud scheduler jobs delete kosodate-scrape-ibaraki-run3 \
    --location=$REGION \
    --project=$PROJECT_ID \
    --quiet 2>/dev/null || true

info ""
info "Creating new jobs..."
info ""

# 1回目: 毎月1日の2:00
info "Creating job 1: 毎月1日 2:00"
gcloud scheduler jobs create http kosodate-scrape-ibaraki-run1 \
    --schedule="0 2 1 * *" \
    --uri="${SERVICE_URL}/scrape/08" \
    --http-method=POST \
    --oidc-service-account-email=$SA_EMAIL \
    --headers="Content-Type=application/json" \
    --location=$REGION \
    --project=$PROJECT_ID \
    --time-zone="Asia/Tokyo" \
    --description="茨城県スクレイピング（1回目）: 毎月1日 2:00実行"

# 2回目: 毎月1日の2:15
info "Creating job 2: 毎月1日 2:15"
gcloud scheduler jobs create http kosodate-scrape-ibaraki-run2 \
    --schedule="15 2 1 * *" \
    --uri="${SERVICE_URL}/scrape/08" \
    --http-method=POST \
    --oidc-service-account-email=$SA_EMAIL \
    --headers="Content-Type=application/json" \
    --location=$REGION \
    --project=$PROJECT_ID \
    --time-zone="Asia/Tokyo" \
    --description="茨城県スクレイピング（2回目）: 毎月1日 2:15実行（1回目がタイムアウトした場合の続き）"

# 3回目: 毎月1日の2:30
info "Creating job 3: 毎月1日 2:30"
gcloud scheduler jobs create http kosodate-scrape-ibaraki-run3 \
    --schedule="30 2 1 * *" \
    --uri="${SERVICE_URL}/scrape/08" \
    --http-method=POST \
    --oidc-service-account-email=$SA_EMAIL \
    --headers="Content-Type=application/json" \
    --location=$REGION \
    --project=$PROJECT_ID \
    --time-zone="Asia/Tokyo" \
    --description="茨城県スクレイピング（3回目）: 毎月1日 2:30実行（念のため）"

info ""
info "=========================================="
info "✅ Cloud Scheduler jobs created!"
info "=========================================="
info ""
info "Scheduler jobs:"
gcloud scheduler jobs list --location=$REGION --project=$PROJECT_ID | grep kosodate

info ""
info "=========================================="
info "次のステップ"
info "=========================================="
info "1. テスト実行:"
info "   gcloud scheduler jobs run kosodate-scrape-ibaraki-run1 --location=$REGION --project=$PROJECT_ID"
info ""
info "2. ログ確認:"
info "   gcloud logging read 'resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"iiba-kosodate-passport-scraper\"' --limit 50 --project=$PROJECT_ID"
info ""
info "3. 次回の定期実行: 毎月1日 2:00, 2:15, 2:30"
info ""
