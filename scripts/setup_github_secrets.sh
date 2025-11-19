#!/bin/bash
set -e

# GitHub Secretsセットアップスクリプト
# Usage: ./scripts/setup_github_secrets.sh [staging|production|all]

REPO="iibainc/iiba-kosodate-passport-scraper"
ENVIRONMENT=${1:-all}

# 色付きログ
info() { echo -e "\033[0;32m[INFO]\033[0m $1"; }
warn() { echo -e "\033[0;33m[WARN]\033[0m $1"; }
error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; exit 1; }

# 前提条件チェック
check_prerequisites() {
    info "前提条件をチェック中..."

    if ! command -v gcloud &> /dev/null; then
        error "gcloudコマンドが見つかりません。Google Cloud SDKをインストールしてください。"
    fi

    if ! command -v gh &> /dev/null; then
        error "ghコマンドが見つかりません。GitHub CLIをインストールしてください: brew install gh"
    fi

    # GitHub CLI認証チェック
    if ! gh auth status &> /dev/null; then
        warn "GitHub CLIが認証されていません。認証を開始します..."
        gh auth login
    fi

    info "✅ 前提条件OK"
}

# Staging環境のSecretsを設定
setup_staging() {
    info "🔧 Staging環境のSecretsを設定中..."

    PROJECT_ID="iiba-staging"

    # プロジェクト存在確認
    if ! gcloud projects describe $PROJECT_ID &> /dev/null; then
        error "プロジェクト $PROJECT_ID が見つかりません。"
    fi

    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
    SA_EMAIL="kosodate-scraper-sa@${PROJECT_ID}.iam.gserviceaccount.com"
    WIF_PROVIDER="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions/providers/github-provider"

    info "PROJECT_NUMBER: $PROJECT_NUMBER"
    info "SA_EMAIL: $SA_EMAIL"
    info "WIF_PROVIDER: $WIF_PROVIDER"

    # GitHub Secretsを設定
    info "GitHub Secretsを設定中..."

    echo "$WIF_PROVIDER" | gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER \
        --repo "$REPO" \
        || error "GCP_WORKLOAD_IDENTITY_PROVIDERの設定に失敗しました"

    echo "$SA_EMAIL" | gh secret set GCP_SERVICE_ACCOUNT \
        --repo "$REPO" \
        || error "GCP_SERVICE_ACCOUNTの設定に失敗しました"

    info "✅ Staging環境のSecretsを設定完了"
}

# Production環境のSecretsを設定
setup_production() {
    info "🔧 Production環境のSecretsを設定中..."

    PROJECT_ID="iiba-production"

    # プロジェクト存在確認
    if ! gcloud projects describe $PROJECT_ID &> /dev/null; then
        error "プロジェクト $PROJECT_ID が見つかりません。"
    fi

    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
    SA_EMAIL="kosodate-scraper-sa@${PROJECT_ID}.iam.gserviceaccount.com"
    WIF_PROVIDER="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions/providers/github-provider"

    info "PROJECT_NUMBER: $PROJECT_NUMBER"
    info "SA_EMAIL: $SA_EMAIL"
    info "WIF_PROVIDER: $WIF_PROVIDER"

    # GitHub Secretsを設定
    info "GitHub Secretsを設定中..."

    echo "$WIF_PROVIDER" | gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER_PROD \
        --repo "$REPO" \
        || error "GCP_WORKLOAD_IDENTITY_PROVIDER_PRODの設定に失敗しました"

    echo "$SA_EMAIL" | gh secret set GCP_SERVICE_ACCOUNT_PROD \
        --repo "$REPO" \
        || error "GCP_SERVICE_ACCOUNT_PRODの設定に失敗しました"

    info "✅ Production環境のSecretsを設定完了"
}

# Secretsの一覧を表示
list_secrets() {
    info "📋 現在のGitHub Secrets:"
    gh secret list --repo "$REPO"
}

# メイン処理
main() {
    info "=========================================="
    info "GitHub Secrets セットアップスクリプト"
    info "=========================================="
    info "環境: $ENVIRONMENT"
    info "リポジトリ: $REPO"
    info ""

    check_prerequisites

    case "$ENVIRONMENT" in
        staging)
            setup_staging
            ;;
        production)
            setup_production
            ;;
        all)
            setup_staging
            echo ""
            setup_production
            ;;
        *)
            error "無効な環境: $ENVIRONMENT (staging, production, all のいずれかを指定)"
            ;;
    esac

    echo ""
    list_secrets

    info ""
    info "=========================================="
    info "✅ セットアップ完了！"
    info "=========================================="
    info "次のステップ:"
    info "1. GitHub Actionsでテスト実行"
    info "   gh workflow run deploy-staging.yml"
    info "2. ログを確認"
    info "   gh run list --workflow=deploy-staging.yml"
}

main
