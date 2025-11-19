.PHONY: help install install-dev format lint typecheck test test-cov clean docker-build docker-run deploy-staging deploy-production release dev-setup dev-start dev-stop dev-run dev-debug

# デフォルトターゲット
.DEFAULT_GOAL := help

# 変数定義
PYTHON := python3.11
PIP := $(PYTHON) -m pip

# Staging環境
PROJECT_ID_STAGING := iiba-staging
# Production環境
PROJECT_ID_PROD := iiba-production

# 共通設定
REGION := asia-northeast1
SERVICE_NAME := iiba-kosodate-passport-scraper

# デフォルトはStaging
PROJECT_ID ?= $(PROJECT_ID_STAGING)
IMAGE_NAME := gcr.io/$(PROJECT_ID)/$(SERVICE_NAME)

help: ## ヘルプを表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 本番依存関係をインストール
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-dev: ## 開発依存関係をインストール
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt

format: ## コードをフォーマット（black, isort）
	@echo "Running black..."
	black src/ tests/
	@echo "Running isort..."
	isort src/ tests/
	@echo "✓ Formatting completed"

lint: ## Lintチェック（black, isort, flake8）
	@echo "Checking black..."
	black --check src/ tests/
	@echo "Checking isort..."
	isort --check-only src/ tests/
	@echo "Running flake8..."
	flake8 src/ tests/
	@echo "✓ Lint check passed"

typecheck: ## 型チェック（mypy）
	@echo "Running mypy..."
	mypy src/
	@echo "✓ Type check passed"

test: ## テストを実行
	@echo "Running tests..."
	pytest
	@echo "✓ Tests passed"

test-cov: ## カバレッジ付きでテストを実行
	@echo "Running tests with coverage..."
	pytest --cov=src --cov-report=html --cov-report=term-missing
	@echo "✓ Coverage report generated in htmlcov/"

clean: ## 一時ファイルとキャッシュを削除
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf htmlcov/ .coverage build/ dist/
	@echo "✓ Cleanup completed"

docker-build: ## Dockerイメージをビルド
	@echo "Building Docker image..."
	docker build -t $(SERVICE_NAME):latest .
	@echo "✓ Docker image built: $(SERVICE_NAME):latest"

docker-run: ## Dockerコンテナをローカルで実行
	@echo "Running Docker container..."
	docker run -p 8080:8080 \
		--env-file .env \
		$(SERVICE_NAME):latest

docker-build-gcp: ## GCP用のDockerイメージをビルド
	@echo "Building Docker image for GCP..."
	gcloud builds submit --tag $(IMAGE_NAME):latest
	@echo "✓ Docker image built and pushed: $(IMAGE_NAME):latest"

deploy-staging: ## Staging環境へデプロイ
	@echo "Deploying to Cloud Run (staging)..."
	@echo "Project: $(PROJECT_ID_STAGING)"
	@echo "Service: $(SERVICE_NAME)"
	@echo "Region: $(REGION)"
	gcloud run deploy $(SERVICE_NAME) \
		--image gcr.io/$(PROJECT_ID_STAGING)/$(SERVICE_NAME):latest \
		--platform managed \
		--region $(REGION) \
		--project $(PROJECT_ID_STAGING) \
		--allow-unauthenticated \
		--set-env-vars="ENVIRONMENT=staging" \
		--set-env-vars="GCP_PROJECT_ID=$(PROJECT_ID_STAGING)" \
		--memory 1Gi \
		--cpu 1 \
		--timeout 3600 \
		--min-instances 0 \
		--max-instances 10
	@echo "✓ Deployment completed"

deploy-production: ## Production環境へデプロイ（タグ必須）
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ Error: VERSION is required for production deployment"; \
		echo "Usage: make deploy-production VERSION=v1.0.0"; \
		exit 1; \
	fi
	@echo "Deploying to Cloud Run (production)..."
	@echo "Project: $(PROJECT_ID_PROD)"
	@echo "Service: $(SERVICE_NAME)"
	@echo "Region: $(REGION)"
	@echo "Version: $(VERSION)"
	@echo ""
	@read -p "Deploy $(VERSION) to PRODUCTION? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		gcloud run deploy $(SERVICE_NAME) \
			--image gcr.io/$(PROJECT_ID_PROD)/$(SERVICE_NAME):$(VERSION) \
			--platform managed \
			--region $(REGION) \
			--project $(PROJECT_ID_PROD) \
			--allow-unauthenticated \
			--set-env-vars="ENVIRONMENT=production" \
			--set-env-vars="GCP_PROJECT_ID=$(PROJECT_ID_PROD)" \
			--memory 2Gi \
			--cpu 2 \
			--timeout 3600 \
			--min-instances 0 \
			--max-instances 20; \
		echo "✓ Production deployment completed"; \
	else \
		echo "Deployment cancelled"; \
		exit 1; \
	fi

release: ## 新しいバージョンをリリース（タグを作成してpush）
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ Error: VERSION is required"; \
		echo "Usage: make release VERSION=v1.0.0"; \
		exit 1; \
	fi
	@echo "Creating release $(VERSION)..."
	@if git rev-parse $(VERSION) >/dev/null 2>&1; then \
		echo "❌ Error: Tag $(VERSION) already exists"; \
		exit 1; \
	fi
	@echo "Current branch: $$(git branch --show-current)"
	@echo "Latest commit: $$(git log -1 --oneline)"
	@echo ""
	@read -p "Create tag $(VERSION) and trigger production deployment? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		git tag -a $(VERSION) -m "Release $(VERSION)"; \
		git push origin $(VERSION); \
		echo "✓ Tag $(VERSION) created and pushed"; \
		echo "✓ GitHub Actions will deploy to production automatically"; \
	else \
		echo "Release cancelled"; \
		exit 1; \
	fi

gcp-config: ## GCP設定を確認
	@echo "Current GCP configuration:"
	@echo "  Project: $$(gcloud config get-value project)"
	@echo "  Account: $$(gcloud config get-value account)"
	@echo "  Region: $$(gcloud config get-value run/region)"

gcp-logs: ## Cloud Runのログを表示
	gcloud run services logs read $(SERVICE_NAME) \
		--project $(PROJECT_ID) \
		--region $(REGION) \
		--limit 50

ci: format lint typecheck test ## CI/CDで実行する全チェック
	@echo "✓ All CI checks passed"

# ローカル開発用タスク
dev-setup: ## ローカル開発環境のセットアップ
	@echo "Setting up local development environment..."
	@echo "1. Installing dependencies..."
	$(MAKE) install-dev
	@echo "2. Copying .env.development to .env..."
	cp .env.development .env
	@echo "✓ Development environment setup completed"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Start Firestore emulator: make dev-start"
	@echo "  2. Run the application: make dev-run"
	@echo "  3. Access Firestore UI: http://localhost:4000"

dev-start: ## Firestoreエミュレータを起動
	@echo "Starting Firestore emulator..."
	docker-compose up -d
	@echo "✓ Firestore emulator started"
	@echo "  Firestore: http://localhost:8080"
	@echo "  Firestore UI: http://localhost:4000"

dev-stop: ## Firestoreエミュレータを停止
	@echo "Stopping Firestore emulator..."
	docker-compose down
	@echo "✓ Firestore emulator stopped"

dev-run: ## ローカル開発環境でアプリケーションを起動
	@echo "Starting application (development mode)..."
	@echo "Loading .env.development..."
	@if [ ! -f .env ]; then \
		echo "Creating .env from .env.development..."; \
		cp .env.development .env; \
	fi
	@export $$(cat .env.development | grep -v '^#' | xargs) && \
		$(PYTHON) -m uvicorn src.server:app --reload --host 0.0.0.0 --port 8000 --log-level debug

dev-debug: ## デバッグモードでアプリケーションを起動（pdb利用可能）
	@echo "Starting application (debug mode)..."
	@export $$(cat .env.development | grep -v '^#' | xargs) && \
		$(PYTHON) -m src.server

dev-scrape-ibaraki: ## ローカル環境で茨城県のスクレイピングを実行
	@echo "Running Ibaraki scraping (local)..."
	@export $$(cat .env.development | grep -v '^#' | xargs) && \
		curl -X POST "http://localhost:8000/scrape/08"

dev-logs: ## Firestoreエミュレータのログを表示
	docker-compose logs -f firestore

dev-clean: ## ローカル開発環境をクリーンアップ
	@echo "Cleaning local development environment..."
	$(MAKE) dev-stop
	docker-compose down -v
	rm -f .env
	@echo "✓ Local environment cleaned"

# ==============================================================================
# GitHub Secrets Setup
# ==============================================================================

github-secrets-setup: ## GitHub Secretsをセットアップ（Staging + Production）
	@echo "Setting up GitHub Secrets..."
	./scripts/setup_github_secrets.sh all

github-secrets-staging: ## Staging環境のGitHub Secretsをセットアップ
	@echo "Setting up GitHub Secrets for Staging..."
	./scripts/setup_github_secrets.sh staging

github-secrets-production: ## Production環境のGitHub Secretsをセットアップ
	@echo "Setting up GitHub Secrets for Production..."
	./scripts/setup_github_secrets.sh production

github-secrets-list: ## GitHub Secretsの一覧を表示
	@echo "GitHub Secrets:"
	gh secret list --repo iibainc/iiba-kosodate-passport-scraper

# ==============================================================================
# Cloud Scheduler Setup
# ==============================================================================

scheduler-setup-staging: ## Cloud Schedulerをセットアップ（Staging）
	@echo "Setting up Cloud Scheduler (Staging)..."
	./scripts/setup_cloud_scheduler.sh iiba-staging

scheduler-setup-production: ## Cloud Schedulerをセットアップ（Production）
	@echo "Setting up Cloud Scheduler (Production)..."
	./scripts/setup_cloud_scheduler.sh iiba-production

scheduler-test-staging: ## Cloud Schedulerジョブをテスト実行（Staging）
	@echo "Running Cloud Scheduler job (test)..."
	gcloud scheduler jobs run kosodate-scrape-ibaraki-run1 \
		--location=asia-northeast1 \
		--project=iiba-staging

scheduler-list-staging: ## Cloud Schedulerジョブの一覧を表示（Staging）
	@echo "Cloud Scheduler jobs (Staging):"
	gcloud scheduler jobs list --location=asia-northeast1 --project=iiba-staging | grep kosodate

scheduler-logs-staging: ## Cloud Runのログを表示（Staging）
	@echo "Cloud Run logs (Staging):"
	gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="iiba-kosodate-passport-scraper"' \
		--limit 50 \
		--project=iiba-staging \
		--format=json