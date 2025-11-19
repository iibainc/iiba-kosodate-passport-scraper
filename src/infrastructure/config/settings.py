"""アプリケーション設定（Pydantic Settings）"""
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリケーション設定"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Project
    project_name: str = Field(
        default="iiba-kosodate-passport-scraper",
        description="プロジェクト名",
    )
    environment: str = Field(
        default="development",
        description="環境 (development, staging, production)",
    )

    # GCP
    gcp_project_id: str = Field(
        ...,
        description="GCPプロジェクトID",
    )
    gcp_region: str = Field(
        default="asia-northeast1",
        description="GCPリージョン",
    )

    # Firestore
    firestore_database_id: str = Field(
        default="(default)",
        description="FirestoreデータベースID",
    )
    firestore_emulator_host: Optional[str] = Field(
        default=None,
        description="Firestoreエミュレータのホスト（例: localhost:8080）。設定された場合はエミュレータに接続",
    )
    firestore_shops_collection: str = Field(
        default="shops",
        description="店舗コレクション名",
    )
    firestore_history_collection: str = Field(
        default="scraping_history",
        description="スクレイピング履歴コレクション名",
    )

    # Cloud Storage
    gcs_bucket_name: str = Field(
        ...,
        description="Cloud Storageバケット名",
    )
    gcs_csv_prefix: str = Field(
        default="csv_exports/",
        description="CSVエクスポートのプレフィックス",
    )

    # Geocoding
    google_maps_api_key_secret_name: str = Field(
        default="google-maps-api-key",
        description="Google Maps API KeyのSecret Manager名",
    )
    geocoding_enabled: bool = Field(
        default=True,
        description="ジオコーディングを有効にするか",
    )
    geocoding_cache_enabled: bool = Field(
        default=True,
        description="ジオコーディングキャッシュを有効にするか",
    )
    geocoding_rate_limit: int = Field(
        default=50,
        description="ジオコーディングのレート制限（リクエスト/秒）",
    )
    google_maps_api_key: Optional[str] = Field(
        default=None,
        description="Google Maps API Key（ローカル開発用）",
    )

    # Scraping
    target_prefectures: str = Field(
        default="08",
        description="対象都道府県コード（カンマ区切り）",
    )
    scraping_timeout: int = Field(
        default=20,
        description="スクレイピングのタイムアウト（秒）",
    )
    scraping_retry: int = Field(
        default=3,
        description="スクレイピングのリトライ回数",
    )
    scraping_user_agent: str = Field(
        default="Mozilla/5.0 (compatible; IIBA-KosodateScraper/1.0)",
        description="スクレイピングのUser-Agent",
    )
    scraping_min_wait: float = Field(
        default=1.0,
        description="スクレイピングの最小待機時間（秒）",
    )
    scraping_max_wait: float = Field(
        default=1.8,
        description="スクレイピングの最大待機時間（秒）",
    )

    # Slack
    slack_webhook_secret_name: str = Field(
        default="slack-webhook-url",
        description="Slack Webhook URLのSecret Manager名",
    )
    slack_channel: str = Field(
        default="#kosodate-scraper-notifications",
        description="Slack通知チャンネル",
    )
    slack_enabled: bool = Field(
        default=True,
        description="Slack通知を有効にするか",
    )
    slack_webhook_url: Optional[str] = Field(
        default=None,
        description="Slack Webhook URL（ローカル開発用）",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    gcp_logging_enabled: bool = Field(
        default=False,
        description="Cloud Loggingを有効にするか",
    )

    # Cloud Run
    port: int = Field(
        default=8080,
        description="HTTPサーバーのポート番号",
    )

    def get_target_prefecture_codes(self) -> list[str]:
        """対象都道府県コードのリストを取得"""
        return [code.strip() for code in self.target_prefectures.split(",")]

    @property
    def is_production(self) -> bool:
        """本番環境かどうか"""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """開発環境かどうか"""
        return self.environment.lower() == "development"
