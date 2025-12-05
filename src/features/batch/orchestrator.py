"""バッチオーケストレーター"""

from typing import Optional

from ...infrastructure.config.settings import Settings
from ...infrastructure.gcp.secret_manager import SecretManagerClient
from ...shared.http.client import HTTPClient
from ...shared.logging.config import get_logger
from ..geocoding.services.geocoding_service import GeocodingService
from ..notifications.providers.slack_notifier import SlackNotifier
from ..scraping.scrapers.prefectures.ibaraki import IbarakiScraper
from ..scraping.scrapers.prefectures.kyoto import KyotoScraper
from ..scraping.scrapers.prefectures.tokyo_csv_scraper import TokyoCsvScraper
from ..storage.clients.firestore_client import FirestoreClient
from ..storage.repositories.history_repository import HistoryRepository
from ..storage.repositories.progress_repository import ProgressRepository
from ..storage.repositories.shop_repository import ShopRepository
from .jobs.prefecture_scraping_job import PrefectureScrapingJob

logger = get_logger(__name__)


class BatchOrchestrator:
    """
    バッチオーケストレーター

    各Featureを統合し、依存性注入を行う
    """

    def __init__(self, settings: Settings) -> None:
        """
        Args:
            settings: アプリケーション設定
        """
        self.settings = settings

        # Secret Managerクライアントを初期化
        self.secret_manager: Optional[SecretManagerClient] = None
        if not settings.is_development:
            self.secret_manager = SecretManagerClient(settings.gcp_project_id)

        # Firestoreクライアントを初期化
        self.firestore_client = FirestoreClient(
            project_id=settings.gcp_project_id,
            database_id=settings.firestore_database_id,
        )

        # リポジトリを初期化
        self.shop_repository = ShopRepository(self.firestore_client)
        self.history_repository = HistoryRepository(self.firestore_client)
        self.progress_repository = ProgressRepository(self.firestore_client)

        # ジオコーディングサービスを初期化（任意）
        self.geocoding_service = self._create_geocoding_service()

        # Slack通知プロバイダーを初期化
        self.slack_notifier = self._create_slack_notifier()

        logger.info("BatchOrchestrator initialized")

    def run_ibaraki_scraping(self) -> None:
        """茨城県のスクレイピングジョブを実行"""
        logger.info("Starting Ibaraki scraping job")

        # HTTPクライアントを作成
        http_client = HTTPClient(
            timeout=self.settings.scraping_timeout,
            max_retries=self.settings.scraping_retry,
            user_agent=self.settings.scraping_user_agent,
        )

        # スクレイパーを作成
        scraper = IbarakiScraper(http_client=http_client)

        # ジョブを実行
        job = PrefectureScrapingJob(
            scraper=scraper,
            geocoding_service=self.geocoding_service,
            shop_repository=self.shop_repository,
            history_repository=self.history_repository,
            progress_repository=self.progress_repository,
            slack_notifier=self.slack_notifier,
        )

        result = job.execute()

        logger.info(f"Ibaraki scraping job completed: {result.status.value}")

    def run_tokyo_scraping(self) -> None:
        """東京都のスクレイピングジョブを実行"""
        logger.info("Starting Tokyo scraping job")

        # HTTPクライアントを作成
        http_client = HTTPClient(
            timeout=self.settings.scraping_timeout,
            max_retries=self.settings.scraping_retry,
            user_agent=self.settings.scraping_user_agent,
        )

        # スクレイパーを作成（CSV方式）
        scraper = TokyoCsvScraper(http_client=http_client)

        # ジョブを実行
        job = PrefectureScrapingJob(
            scraper=scraper,
            geocoding_service=self.geocoding_service,
            shop_repository=self.shop_repository,
            history_repository=self.history_repository,
            progress_repository=self.progress_repository,
            slack_notifier=self.slack_notifier,
        )

        result = job.execute()

        logger.info(f"Tokyo scraping job completed: {result.status.value}")

    def run_kyoto_scraping(self) -> None:
        """京都府のスクレイピングジョブを実行"""
        logger.info("Starting Kyoto scraping job")

        # HTTPクライアントを作成
        http_client = HTTPClient(
            timeout=self.settings.scraping_timeout,
            max_retries=self.settings.scraping_retry,
            user_agent=self.settings.scraping_user_agent,
        )

        # スクレイパーを作成
        scraper = KyotoScraper(http_client=http_client)

        # ジョブを実行
        job = PrefectureScrapingJob(
            scraper=scraper,
            geocoding_service=self.geocoding_service,
            shop_repository=self.shop_repository,
            history_repository=self.history_repository,
            progress_repository=self.progress_repository,
            slack_notifier=self.slack_notifier,
        )

        result = job.execute()

        logger.info(f"Kyoto scraping job completed: {result.status.value}")

    def run_prefecture_scraping(self, prefecture_code: str) -> None:
        """
        指定された都道府県のスクレイピングジョブを実行

        Args:
            prefecture_code: 都道府県コード

        Raises:
            ValueError: サポートされていない都道府県コードの場合
        """
        logger.info(f"Starting scraping job for prefecture: {prefecture_code}")

        if prefecture_code == "08":
            self.run_ibaraki_scraping()
        elif prefecture_code == "13":
            self.run_tokyo_scraping()
        elif prefecture_code == "26":
            self.run_kyoto_scraping()
        else:
            raise ValueError(
                f"Unsupported prefecture code: {prefecture_code}. "
                f"Currently, only Ibaraki (08) , Tokyo (13) and Kyoto (26) are supported."
            )

    def run_all_target_prefectures(self) -> None:
        """設定で指定された全都道府県のスクレイピングを実行"""
        target_codes = self.settings.get_target_prefecture_codes()

        logger.info(f"Starting scraping for {len(target_codes)} prefectures")

        for code in target_codes:
            try:
                self.run_prefecture_scraping(code)
            except Exception as e:
                logger.error(f"Failed to scrape prefecture {code}: {e}")
                # 他の都道府県の処理を続行

        logger.info("All prefecture scraping jobs completed")

    def _create_geocoding_service(self) -> Optional[GeocodingService]:
        """
        ジオコーディングサービスを作成

        Returns:
            Optional[GeocodingService]: ジオコーディングサービス
        """
        if not self.settings.geocoding_enabled:
            logger.info("Geocoding is disabled via settings; skipping service initialization")
            return None

        # Google Maps API Keyを取得
        api_key = self.settings.google_maps_api_key

        if not api_key and self.secret_manager:
            # Secret Managerから取得
            try:
                api_key = self.secret_manager.get_secret(
                    self.settings.google_maps_api_key_secret_name
                )
            except Exception as e:
                logger.error(f"Failed to get Google Maps API key from Secret Manager: {e}")
                raise

        if not api_key:
            raise ValueError("Google Maps API key is required for geocoding")

        # レート制限の計算
        delay = 1.0 / self.settings.geocoding_rate_limit

        return GeocodingService(
            api_key=api_key,
            use_cache=self.settings.geocoding_cache_enabled,
            delay_between_requests=delay,
        )

    def _create_slack_notifier(self) -> Optional[SlackNotifier]:
        """
        Slack通知プロバイダーを作成

        Returns:
            Optional[SlackNotifier]: Slack通知プロバイダー（無効の場合はNone）
        """
        if not self.settings.slack_enabled:
            logger.info("Slack notifications are disabled")
            return None

        # Slack Webhook URLを取得
        webhook_url = self.settings.slack_webhook_url

        if not webhook_url and self.secret_manager:
            # Secret Managerから取得
            try:
                webhook_url = self.secret_manager.get_secret(
                    self.settings.slack_webhook_secret_name
                )
            except Exception as e:
                logger.warning(f"Failed to get Slack webhook URL from Secret Manager: {e}")
                return None

        if not webhook_url:
            logger.warning("Slack webhook URL is not configured")
            return None

        return SlackNotifier(
            webhook_url=webhook_url,
            default_channel=self.settings.slack_channel,
        )
