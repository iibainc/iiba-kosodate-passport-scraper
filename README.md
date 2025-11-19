# 子育て支援パスポートスクレイピングサービス

[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://github.com/python/mypy)

全国の子育て支援パスポート加盟店情報をスクレイピングし、Firestoreに保存するGCP Cloud Runバッチサービスです。

## 📋 概要

このサービスは、各都道府県の子育て支援パスポートWebサイトから加盟店情報を取得し、以下のデータをFirestoreに保存します:

- 店名、住所、電話番号
- 営業時間、定休日
- 優待内容、紹介コメント
- 駐車場情報
- **緯度・経度（Google Maps Geocoding APIで自動取得）**

## 🏗️ アーキテクチャ

### Featureアーキテクチャ

```
src/features/
├── scraping/      # Webスクレイピング機能
├── geocoding/     # ジオコーディング機能
├── storage/       # Firestore保存機能
├── notifications/ # Slack通知機能
└── batch/         # バッチオーケストレーション
```

### 技術スタック

- **言語**: Python 3.11
- **Webフレームワーク**: FastAPI（最小限のHTTPサーバー）
- **スクレイピング**: Requests + BeautifulSoup4
- **ジオコーディング**: Google Maps Geocoding API
- **データベース**: Cloud Firestore
- **ストレージ**: Cloud Storage（CSVバックアップ）
- **通知**: Slack Webhook
- **実行基盤**: GCP Cloud Run
- **スケジューラー**: Cloud Scheduler

## 📂 ディレクトリ構造

```
iiba-kosodate-passport-scraper/
├── src/
│   ├── features/          # 機能単位のコード
│   ├── shared/            # 共通ユーティリティ
│   ├── infrastructure/    # インフラ設定
│   ├── entrypoint.py      # CLIエントリーポイント
│   └── server.py          # Cloud Run HTTPサーバー
├── tests/                 # テストコード
├── scripts/               # 運用スクリプト
├── infrastructure/        # Terraform設定
└── docs/                  # ドキュメント
```

## 🚀 セットアップ

### 前提条件

- Python 3.11以上
- GCPプロジェクト
- Google Maps API Key
- Slack Webhook URL（通知用）

### ローカル開発環境

**🎯 クイックスタート（推奨）**

```bash
# 1. リポジトリのクローン
git clone <repository-url>
cd iiba-kosodate-passport-scraper

# 2. 仮想環境の作成と有効化
python3.11 -m venv .venv
source .venv/bin/activate  # macOS/Linux

# 3. 開発環境のセットアップ（依存関係インストール + .env作成）
make dev-setup

# 4. Firestoreエミュレータを起動
make dev-start

# 5. アプリケーションを起動
make dev-run
```

これだけで、ローカル開発環境が立ち上がります！

- アプリケーション: http://localhost:8000
- Firestore UI: http://localhost:4000

**📚 詳細な手順とデバッグ方法:**
- [ローカル開発ガイド (VSCode)](docs/LOCAL_DEVELOPMENT.md)
- [PyCharmデバッグガイド](docs/PYCHARM_SETUP.md)

---

<details>
<summary>手動セットアップ（クリックして展開）</summary>

1. リポジトリのクローン

```bash
git clone <repository-url>
cd iiba-kosodate-passport-scraper
```

2. 仮想環境の作成と有効化

```bash
python3.11 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows
```

3. 依存関係のインストール

```bash
pip install -r requirements-dev.txt
```

4. 環境変数の設定

```bash
cp .env.development .env
# .env ファイルを編集して必要な値を設定
```

5. Docker Composeでエミュレータを起動

```bash
docker-compose up -d
```

6. GCP認証情報の設定（本番環境接続時のみ）

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

</details>

## 💻 使用方法

### ローカル実行

**方法A: Makeコマンド（推奨）**

```bash
# Firestoreエミュレータを起動
make dev-start

# 茨城県のスクレイピングを実行
make dev-scrape-ibaraki

# または直接curlで
curl -X POST "http://localhost:8000/scrape/08"
```

**方法B: スクリプトで直接実行（デバッグ向け）**

```bash
# デバッグモード
python scripts/run_scraping.py --prefecture 08 --debug

# 通常モード
python scripts/run_scraping.py --prefecture 08
```

**方法C: VSCodeデバッガーで実行**

1. `.vscode/launch.json`に設定済み
2. デバッグパネルで **"Scrape Ibaraki (Debug)"** を選択して実行
3. ブレークポイントを設定してステップ実行可能

### テストの実行

```bash
# すべてのテストを実行
pytest

# カバレッジレポート付き
pytest --cov=src --cov-report=html

# 特定のテストのみ
pytest tests/unit/features/scraping/
```

### コード品質チェック

```bash
# フォーマット
black src/ tests/
isort src/ tests/

# 型チェック
mypy src/

# すべてのチェックを一度に
black src/ tests/ && isort src/ tests/ && mypy src/
```

## 🌐 デプロイメント

### クイックスタート

**Staging環境（自動デプロイ）**
```bash
git push origin main
```
`main`ブランチへのpushで自動的にステージング環境へデプロイされます。

**Production環境（タグベースデプロイ）**
```bash
# 新しいバージョンをリリース
make release VERSION=v1.0.0
```
タグをpushすると自動的に本番環境へデプロイされます。

**📚 詳細な手順は [デプロイメントガイド](docs/DEPLOYMENT.md) を参照してください。**

---

## 🔧 GCP初期セットアップ

### 前提条件

- GCPプロジェクト（`iiba-staging` / `iiba-production`）
- Workload Identity Federationの設定
- Artifact Registryリポジトリ

### 1. GCPリソースの準備

#### 1-1. Artifact Registryリポジトリの作成

```bash
gcloud artifacts repositories create kosodate-scraper \
    --repository-format=docker \
    --location=asia-northeast1 \
    --project=iiba-staging
```

#### 1-2. サービスアカウントの作成

```bash
# サービスアカウント作成
gcloud iam service-accounts create kosodate-scraper-sa \
    --display-name="Kosodate Scraper Service Account" \
    --project=iiba-staging

# 必要な権限を付与
gcloud projects add-iam-policy-binding iiba-staging \
    --member="serviceAccount:kosodate-scraper-sa@iiba-staging.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding iiba-staging \
    --member="serviceAccount:kosodate-scraper-sa@iiba-staging.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding iiba-staging \
    --member="serviceAccount:kosodate-scraper-sa@iiba-staging.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

### 2. Secret Managerへのシークレット登録

```bash
# Google Maps API Key
echo -n "YOUR_API_KEY" | gcloud secrets create google-maps-api-key \
    --data-file=- \
    --replication-policy="automatic" \
    --project=iiba-staging

# Slack Webhook URL
echo -n "YOUR_WEBHOOK_URL" | gcloud secrets create slack-webhook-url \
    --data-file=- \
    --replication-policy="automatic" \
    --project=iiba-staging
```

### 3. Workload Identity Federationの設定

```bash
# Workload Identity Poolの作成
gcloud iam workload-identity-pools create "github-pool" \
    --project="iiba-staging" \
    --location="global" \
    --display-name="GitHub Actions Pool"

# GitHub Providerの作成
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
    --project="iiba-staging" \
    --location="global" \
    --workload-identity-pool="github-pool" \
    --display-name="GitHub Provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
    --issuer-uri="https://token.actions.githubusercontent.com"

# サービスアカウントへの権限付与
gcloud iam service-accounts add-iam-policy-binding \
    kosodate-scraper-sa@iiba-staging.iam.gserviceaccount.com \
    --project="iiba-staging" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/YOUR_GITHUB_ORG/iiba-kosodate-passport-scraper"
```

### 4. GitHub Secretsの設定

GitHubリポジトリの Settings > Secrets and variables > Actions で以下を設定：

- `GCP_WORKLOAD_IDENTITY_PROVIDER`: `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider`
- `GCP_SERVICE_ACCOUNT`: `kosodate-scraper-sa@iiba-staging.iam.gserviceaccount.com`

### 5. デプロイ

#### GitHub Actions経由（推奨）

mainブランチにpushすると自動的にデプロイされます：

```bash
git push origin main
```

#### ローカルからのデプロイ

```bash
# Makefileを使用
make docker-build-gcp
make deploy-staging

# または直接gcloudコマンドで
gcloud run deploy iiba-kosodate-passport-scraper \
    --image asia-northeast1-docker.pkg.dev/iiba-staging/kosodate-scraper/iiba-kosodate-passport-scraper:latest \
    --platform managed \
    --region asia-northeast1 \
    --project iiba-staging \
    --allow-unauthenticated
```

### 6. Cloud Schedulerの設定（都道府県ごと）

```bash
# 茨城県（毎月1日 2:00実行）
gcloud scheduler jobs create http kosodate-scrape-ibaraki \
    --schedule="0 2 1 * *" \
    --uri="https://YOUR_CLOUD_RUN_URL/scrape/08" \
    --http-method=POST \
    --oidc-service-account-email=kosodate-scraper-sa@iiba-staging.iam.gserviceaccount.com \
    --headers="Content-Type=application/json" \
    --location=asia-northeast1 \
    --project=iiba-staging

# 他の都道府県も同様に追加可能
```

### 7. デプロイの確認

```bash
# サービスURLを取得
gcloud run services describe iiba-kosodate-passport-scraper \
    --region asia-northeast1 \
    --project iiba-staging \
    --format='value(status.url)'

# ヘルスチェック
curl https://YOUR_SERVICE_URL/health

# ログの確認
make gcp-logs
```

## 📊 Firestoreスキーマ

### shops コレクション

```json
{
  "shop_id": "08_00001",
  "prefecture_code": "08",
  "prefecture_name": "茨城県",
  "name": "○○○○ 水戸店",
  "address": "茨城県水戸市○○町1-2-3",
  "phone": "029-123-4567",
  "business_hours": "10:00-22:00",
  "closed_days": "火曜日",
  "detail_url": "https://...",
  "website": "https://...",
  "benefits": "会計時10%割引",
  "description": "お子様連れ大歓迎",
  "parking": "あり（50台）",
  "latitude": 36.341811,
  "longitude": 140.446793,
  "geocoded_at": "2025-01-15T12:00:00Z",
  "scraped_at": "2025-01-15T12:00:00Z",
  "updated_at": "2025-01-15T12:00:00Z",
  "is_active": true
}
```

## 🔧 トラブルシューティング

### ジオコーディングが失敗する

- Google Maps APIキーが正しく設定されているか確認
- APIの使用量制限を確認（無料枠: 28,500リクエスト/月）
- Geocoding APIが有効になっているか確認

### Firestoreへの書き込みが失敗する

- サービスアカウントに適切な権限があるか確認
- Firestoreがプロジェクトで有効になっているか確認

### Cloud Runのタイムアウト

- 実行時間が長い場合は、対象ページ数を分割して複数回実行
- Cloud Runのタイムアウト設定を延長（最大3600秒）

## 📚 ドキュメント

- [アーキテクチャ詳細](docs/architecture.md)
- [デプロイ手順](docs/deployment.md)
- [運用マニュアル](docs/operations.md)
- [茨城県実装詳細](docs/prefectures/ibaraki.md)

## 💰 コスト見積もり

| サービス | 月額コスト |
|---------|----------|
| Cloud Run | $0.50 |
| Firestore | $0.20 |
| Cloud Storage | $0.01 |
| Cloud Scheduler | $0.10 |
| Cloud Logging | $0.25 |
| Google Maps API | $0.00（無料枠内） |
| **合計** | **約$1.06/月** |

※Google Maps APIは月28,500リクエストまで無料（$200クレジット）

## 🤝 貢献

バグ報告や機能リクエストは、GitHubのIssueでお願いします。

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 👥 作成者

IIBA Team
