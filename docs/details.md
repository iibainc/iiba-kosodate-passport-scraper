# 子育て支援パスポートスクレイピングサービス実装の継続

  ## プロジェクト概要

  全国の子育て支援パスポート加盟店情報をスクレイピングし、Firestoreに保存するGCP Cloud Runバッチサービスを構築中です。

  ## 現在の状態

  ### 完了済み（Phase 1-3）
  ✅ **Phase 1: プロジェクト基盤構築**
  - ディレクトリ構造作成（Featureアーキテクチャ）
  - requirements.txt, pyproject.toml, .env.example, .gitignore, README.md作成済み

  ✅ **Phase 2: Domain層実装**
  - `src/features/scraping/domain/enums.py` - PrefectureCode, ScrapingStatus
  - `src/features/scraping/domain/models.py` - Shop, ScrapingResult, Prefecture
  - `src/features/geocoding/domain/models.py` - GeoLocation
  - `src/features/notifications/domain/models.py` - NotificationMessage, NotificationType

  ✅ **Phase 3: 共通レイヤー実装**
  - `src/shared/exceptions/errors.py` - カスタム例外
  - `src/shared/utils/text.py` - テキスト正規化、電話番号・郵便番号抽出
  - `src/shared/utils/datetime_utils.py` - 日時ユーティリティ
  - `src/shared/logging/config.py` - ロギング設定
  - `src/shared/http/client.py` - リトライ付きHTTPクライアント
  - `src/shared/http/rate_limiter.py` - レート制限
  - `src/infrastructure/config/settings.py` - Pydantic Settings
  - `src/infrastructure/gcp/secret_manager.py` - Secret Manager連携

  ### 作業ディレクトリ

  プロジェクトルート: `/Users/diegoalessandrobacigalupomontero/iiba-kosodate-passport-scraper`

  既存の茨城県スクレイパー（リファクタリング前）: `legacy/kidsclub_scrape.py`

  ## 実装が必要な残りのPhase

  ### Phase 4: Storage Feature実装（Firestore、Repository）

  #### 4-1. Firestoreクライアント
  **ファイル**: `src/features/storage/clients/firestore_client.py`

  ```python
  """Firestoreクライアント"""
  from typing import Any, Optional
  from google.cloud import firestore
  from ...shared.logging.config import get_logger
  from ...shared.exceptions.errors import StorageError

  logger = get_logger(__name__)

  class FirestoreClient:
      """Firestore操作クライアント"""

      def __init__(self, project_id: str, database_id: str = "(default)"):
          self.project_id = project_id
          self.database_id = database_id
          self.client = firestore.Client(project=project_id, database=database_id)
          logger.info(f"Firestore client initialized: project={project_id}, database={database_id}")

      def get_collection(self, collection_path: str) -> firestore.CollectionReference:
          """コレクション参照を取得"""
          return self.client.collection(collection_path)

      def batch_write(self, collection_path: str, documents: list[dict[str, Any]], batch_size: int = 500) -> None:
          """バッチ書き込み（500件ずつ）"""
          # 実装内容

  4-2. ShopRepository

  ファイル: src/features/storage/repositories/shop_repository.py

  Shopモデルの保存・更新・検索機能を実装してください。

  4-3. HistoryRepository

  ファイル: src/features/storage/repositories/history_repository.py

  スクレイピング履歴の保存機能を実装してください。

  ---
  Phase 5: Scraping Feature実装（茨城県スクレイパー）

  legacy/kidsclub_scrape.py を参考に、型安全でテスタブルな実装にリファクタリングしてください。

  5-1. 茨城県設定ファイル

  ファイル: src/features/scraping/config/prefectures/ibaraki.yaml

  prefecture:
    code: "08"
    name: "茨城県"
    name_en: "ibaraki"

  scraping:
    base_url: "https://www.kids.pref.ibaraki.jp"
    encoding: "shift_jis"

    urls:
      search_form: "/kids/search_free/xs={xs}/dt=2337/"
      list_page: "/kids/search_free/{page}/xs={xs}/dt=2337,0/"
      detail_pattern: "/kids/.*/dt=2339,\\d+/"

    pagination:
      start_page: 1
      end_page: 247
      auto_detect: false

    session:
      required: true
      token_pattern: "xs=(_[A-Za-z0-9]+)"

    selectors:
      shop_name:
        - "h4"
        - "h1"
        - ".title"
      table: "table tr"
      dl: "dl"

    rate_limit:
      sleep_min: 1.0
      sleep_max: 1.8

  5-2. IbarakiParser

  ファイル: src/features/scraping/parsers/prefectures/ibaraki_parser.py

  HTMLからShopオブジェクトを抽出するパーサーを実装してください。

  5-3. IbarakiScraper

  ファイル: src/features/scraping/scrapers/prefectures/ibaraki.py

  AbstractPrefectureScraperを継承した茨城県スクレイパーを実装してください。

  ---
  Phase 6: Geocoding Feature実装

  6-1. GoogleMapsGeocoder

  ファイル: src/features/geocoding/providers/google_maps_geocoder.py

  """Google Maps Geocoding API実装"""
  import googlemaps
  from typing import Optional
  from ..domain.models import GeoLocation
  from ...shared.exceptions.errors import GeocodingError

  class GoogleMapsGeocoder:
      """Google Maps Geocoding API実装"""

      def __init__(self, api_key: str):
          self.client = googlemaps.Client(key=api_key)

      def geocode(self, address: str) -> Optional[GeoLocation]:
          """住所をジオコーディング"""
          # 実装内容

  6-2. CacheGeocoder

  ファイル: src/features/geocoding/providers/cache_geocoder.py

  重複する住所のAPI呼び出しを削減するキャッシュ機能を実装してください。

  6-3. GeocodingService

  ファイル: src/features/geocoding/services/geocoding_service.py

  バッチジオコーディング機能を実装してください。

  ---
  Phase 7: Notifications Feature実装

  7-1. SlackNotifier

  ファイル: src/features/notifications/providers/slack_notifier.py

  Slack Webhookを使った通知機能を実装してください。Block Kitを使ったリッチメッセージを送信します。

  ---
  Phase 8: Batch Orchestrator実装

  8-1. PrefectureScrapingJob

  ファイル: src/features/batch/jobs/prefecture_scraping_job.py

  以下の処理フローを実装:
  1. スクレイピング開始通知（Slack）
  2. Webサイトからデータ取得
  3. ジオコーディング
  4. Firestore保存
  5. CSVバックアップ（Cloud Storage）
  6. 完了通知

  8-2. BatchOrchestrator

  ファイル: src/features/batch/orchestrator.py

  各Featureを統合し、依存性注入を行うオーケストレーターを実装してください。

  8-3. エントリーポイント

  ファイル: src/entrypoint.py, src/server.py

  CLIとCloud Run用HTTPサーバーを実装してください。

  ---
  Phase 9: テスト実装

  ユニットテスト・統合テストを実装してください。

  ---
  Phase 10: Docker化とデプロイ準備

  Dockerfile

  FROM python:3.11-slim AS builder

  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir --user -r requirements.txt

  FROM python:3.11-slim

  WORKDIR /app
  COPY --from=builder /root/.local /root/.local
  ENV PATH=/root/.local/bin:$PATH

  COPY src/ ./src/
  COPY .env.example .env

  RUN useradd -m appuser && chown -R appuser:appuser /app
  USER appuser

  ENV PORT=8080
  ENV PYTHONUNBUFFERED=1

  CMD ["python", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8080"]

  ---
  Firestoreスキーマ（重要）

  shopsコレクション

  {
    "shop_id": "08_00001",
    "prefecture_code": "08",
    "prefecture_name": "茨城県",
    "name": "店名",
    "address": "住所",
    "phone": "電話番号",
    "business_hours": "営業時間",
    "closed_days": "定休日",
    "detail_url": "詳細URL",
    "website": "ウェブサイト",
    "benefits": "優待内容",
    "description": "紹介コメント",
    "parking": "駐車場",
    "latitude": 36.341811,
    "longitude": 140.446793,
    "geocoded_at": "2025-01-15T12:00:00Z",
    "scraped_at": "2025-01-15T12:00:00Z",
    "updated_at": "2025-01-15T12:00:00Z",
    "is_active": true
  }

  ---
  実装ガイドライン

  1. 型安全性: すべての関数に型ヒントを付ける（mypy検証必須）
  2. エラーハンドリング: 適切な例外処理とログ出力
  3. テスタビリティ: 依存性注入を活用
  4. ドキュメント: 各クラス・関数にdocstringを記述
  5. 参考コード: legacy/kidsclub_scrape.pyを参照しながらリファクタリング

  ---
  タスクリスト

  Phase 4以降を順番に実装してください:
  - Phase 4: Storage Feature
  - Phase 5: Scraping Feature
  - Phase 6: Geocoding Feature
  - Phase 7: Notifications Feature
  - Phase 8: Batch Orchestrator
  - Phase 9: テスト実装
  - Phase 10: Docker化

  実装を開始してください。
