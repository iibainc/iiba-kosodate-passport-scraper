"""都道府県スクレイピングジョブ"""

import uuid
from datetime import datetime
from typing import Optional

from ....shared.exceptions.errors import GeocodingError, ScraperError, StorageError
from ....shared.logging.config import get_logger
from ...geocoding.services.geocoding_service import GeocodingService
from ...notifications.providers.slack_notifier import SlackNotifier
from ...scraping.domain.enums import ScrapingStatus
from ...scraping.domain.models import ScrapingResult
from ...scraping.scrapers.base import AbstractPrefectureScraper
from ...storage.repositories.history_repository import HistoryRepository
from ...storage.repositories.progress_repository import ProgressRepository
from ...storage.repositories.shop_repository import ShopRepository

logger = get_logger(__name__)


class PrefectureScrapingJob:
    """都道府県スクレイピングジョブ"""

    def __init__(
        self,
        scraper: AbstractPrefectureScraper,
        geocoding_service: Optional[GeocodingService],
        shop_repository: ShopRepository,
        history_repository: HistoryRepository,
        progress_repository: ProgressRepository,
        slack_notifier: Optional[SlackNotifier] = None,
        batch_size: int = 50,
    ) -> None:
        """
        Args:
            scraper: 都道府県スクレイパー
            geocoding_service: ジオコーディングサービス
            shop_repository: 店舗リポジトリ
            history_repository: 履歴リポジトリ
            progress_repository: 進捗リポジトリ
            slack_notifier: Slack通知プロバイダー（オプション）
            batch_size: バッチサイズ（店舗数）
        """
        self.scraper = scraper
        self.geocoding_service = geocoding_service
        self.shop_repository = shop_repository
        self.history_repository = history_repository
        self.progress_repository = progress_repository
        self.slack_notifier = slack_notifier
        self.batch_size = batch_size

        # バッチ処理の統計
        self.total_processed = 0
        self.total_geocoded = 0
        self.total_created = 0
        self.total_updated = 0

        # 進捗管理
        self.completed_pages: list[int] = []

        logger.info(
            f"PrefectureScrapingJob initialized: {self.scraper.prefecture_name} (batch_size={batch_size})"
        )

    def execute(self) -> ScrapingResult:
        """
        スクレイピングジョブを実行

        処理フロー:
        1. スクレイピング開始通知（Slack）
        2. Webサイトからデータ取得
        3. ジオコーディング
        4. Firestore保存
        5. 完了通知

        Returns:
            ScrapingResult: スクレイピング結果
        """
        # 実行IDを生成
        run_id = f"{self.scraper.prefecture_code}_{uuid.uuid4().hex[:8]}"
        started_at = datetime.now()

        # スクレイピング結果オブジェクトを初期化
        result = ScrapingResult(
            run_id=run_id,
            prefecture_code=self.scraper.prefecture_code,
            prefecture_name=self.scraper.prefecture_name,
            started_at=started_at,
            status=ScrapingStatus.RUNNING,
        )

        try:
            logger.info(f"Starting scraping job: {self.scraper.prefecture_name} (run_id={run_id})")

            # 1. スクレイピング開始通知
            self._send_start_notification()

            # 2. 前回の進捗を確認
            previous_progress = self.progress_repository.get_progress(self.scraper.prefecture_code)
            resume_from_page = None
            if previous_progress:
                completed_pages = previous_progress.get("completed_pages", [])
                if completed_pages:
                    # 最後に完了したページの次から再開
                    resume_from_page = max(completed_pages) + 1
                    self.completed_pages = completed_pages
                    self.total_processed = previous_progress.get("total_shops_saved", 0)
                    logger.info(
                        f"Resuming from page {resume_from_page}, "
                        f"{len(completed_pages)} pages already completed, "
                        f"{self.total_processed} shops already saved"
                    )

            # 3. Webサイトからデータ取得（バッチ処理付き）
            logger.info(
                f"Step 1: Scraping shops from website with batch processing (batch_size={self.batch_size})"
            )

            # バッチコールバックを定義
            def process_batch(batch_shops: list) -> None:
                """バッチ処理：ジオコーディングと保存"""
                try:
                    logger.info(f"Processing batch of {len(batch_shops)} shops")

                    # ジオコーディング
                    geocoding_result = self._geocode_shops(batch_shops)
                    self.total_geocoded += geocoding_result["success"]

                    # Firestore保存
                    save_result = self._save_shops(batch_shops)
                    self.total_created += save_result["created"]
                    self.total_updated += save_result["updated"]
                    self.total_processed += len(batch_shops)

                    logger.info(
                        f"Batch processed: {len(batch_shops)} shops, "
                        f"{save_result['created']} new, {save_result['updated']} updated, "
                        f"{geocoding_result['success']} geocoded"
                    )
                    logger.info(
                        f"Total progress: {self.total_processed} shops processed, "
                        f"{self.total_created} created, {self.total_updated} updated"
                    )
                except Exception as e:
                    logger.error(f"Batch processing failed: {e}", exc_info=True)

            # ページ完了コールバックを定義
            def on_page_complete(page_num: int) -> None:
                """ページ完了時の処理"""
                self.completed_pages.append(page_num)
                # 進捗を保存
                last_shop_id = f"{self.scraper.prefecture_code}_{self.total_processed:05d}"
                self.progress_repository.save_progress(
                    prefecture_code=self.scraper.prefecture_code,
                    completed_pages=self.completed_pages,
                    total_shops_saved=self.total_processed,
                    last_shop_id=last_shop_id,
                )
                logger.info(f"Page {page_num} completed and progress saved")

            # スクレイピング実行（バッチコールバック付き）
            shops = self.scraper.scrape(
                batch_callback=process_batch,
                batch_size=self.batch_size,
                resume_from_page=resume_from_page,
                page_complete_callback=on_page_complete,
            )
            result.total_shops = len(shops)

            if not shops:
                logger.warning("No shops found")
                result.status = ScrapingStatus.SUCCESS
                result.completed_at = datetime.now()
                result.duration_seconds = (result.completed_at - started_at).total_seconds()

                # 履歴を保存
                self.history_repository.save(result)

                # 完了通知
                self._send_complete_notification(result)

                return result

            logger.info(f"Found {len(shops)} shops")

            # バッチ処理で既に保存済みなので、ここでは統計を集計するのみ
            result.geocoded_shops = self.total_geocoded
            result.new_shops = self.total_created
            result.updated_shops = self.total_updated

            # 完了
            result.status = ScrapingStatus.SUCCESS
            result.completed_at = datetime.now()
            result.duration_seconds = (result.completed_at - started_at).total_seconds()

            logger.info(
                f"Scraping job completed: {result.total_shops} shops, "
                f"{result.new_shops} new, {result.updated_shops} updated, "
                f"{result.geocoded_shops} geocoded"
            )

            # 履歴を保存
            self.history_repository.save(result)

            # 進捗をクリア（完了したため）
            self.progress_repository.clear_progress(self.scraper.prefecture_code)

            # 完了通知
            self._send_complete_notification(result)

            return result

        except ScraperError as e:
            logger.error(f"Scraping error: {e}")
            result.status = ScrapingStatus.FAILED
            result.errors.append(f"ScraperError: {str(e)}")
            return self._handle_error(result, started_at, str(e))

        except GeocodingError as e:
            logger.error(f"Geocoding error: {e}")
            result.status = ScrapingStatus.PARTIAL
            result.errors.append(f"GeocodingError: {str(e)}")
            return self._handle_error(result, started_at, str(e))

        except StorageError as e:
            logger.error(f"Storage error: {e}")
            result.status = ScrapingStatus.FAILED
            result.errors.append(f"StorageError: {str(e)}")
            return self._handle_error(result, started_at, str(e))

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            result.status = ScrapingStatus.FAILED
            result.errors.append(f"UnexpectedError: {str(e)}")
            return self._handle_error(result, started_at, str(e))

    def _geocode_shops(self, shops: list, show_progress: bool = False) -> dict[str, int]:
        """
        店舗のジオコーディング

        Args:
            shops: 店舗リスト
            show_progress: 進捗表示の有無

        Returns:
            dict[str, int]: ジオコーディング結果
        """
        if not self.geocoding_service:
            logger.info("Geocoding is disabled; skipping geocoding for current batch")
            return {
                "success": 0,
                "failure": 0,
                "skipped": len(shops),
                "total": len(shops),
            }

        try:
            result = self.geocoding_service.geocode_shops_batch(shops, show_progress=show_progress)
            logger.debug(
                f"Geocoding completed: {result['success']} success, " f"{result['failure']} failure"
            )
            return result

        except Exception as e:
            logger.error(f"Geocoding failed: {e}")
            return {
                "success": 0,
                "failure": len(shops),
                "skipped": 0,
                "total": len(shops),
            }

    def _save_shops(self, shops: list) -> dict[str, int]:
        """
        店舗をFirestoreに保存

        Args:
            shops: 店舗リスト

        Returns:
            dict[str, int]: 保存結果
        """
        try:
            result = self.shop_repository.save_batch(shops)
            logger.info(
                f"Shops saved: {result['created']} created, " f"{result['updated']} updated"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to save shops: {e}")
            raise StorageError(f"Failed to save shops: {e}") from e

    def _send_start_notification(self) -> None:
        """スクレイピング開始通知を送信"""
        if self.slack_notifier:
            try:
                self.slack_notifier.send_scraping_start(
                    self.scraper.prefecture_name, self.scraper.prefecture_code
                )
            except Exception as e:
                logger.warning(f"Failed to send start notification: {e}")

    def _send_complete_notification(self, result: ScrapingResult) -> None:
        """スクレイピング完了通知を送信"""
        if self.slack_notifier:
            try:
                self.slack_notifier.send_scraping_complete(
                    prefecture_name=result.prefecture_name,
                    prefecture_code=result.prefecture_code,
                    total_shops=result.total_shops,
                    new_shops=result.new_shops,
                    updated_shops=result.updated_shops,
                    geocoded_shops=result.geocoded_shops,
                    duration_seconds=result.duration_seconds or 0.0,
                )
            except Exception as e:
                logger.warning(f"Failed to send complete notification: {e}")

    def _send_error_notification(self, error_message: str) -> None:
        """エラー通知を送信"""
        if self.slack_notifier:
            try:
                self.slack_notifier.send_scraping_error(
                    prefecture_name=self.scraper.prefecture_name,
                    prefecture_code=self.scraper.prefecture_code,
                    error=error_message,
                )
            except Exception as e:
                logger.warning(f"Failed to send error notification: {e}")

    def _handle_error(
        self, result: ScrapingResult, started_at: datetime, error_message: str
    ) -> ScrapingResult:
        """
        エラーハンドリング

        Args:
            result: スクレイピング結果
            started_at: 開始時刻
            error_message: エラーメッセージ

        Returns:
            ScrapingResult: 更新されたスクレイピング結果
        """
        result.completed_at = datetime.now()
        result.duration_seconds = (result.completed_at - started_at).total_seconds()

        # 履歴を保存
        try:
            self.history_repository.save(result)
        except Exception as e:
            logger.error(f"Failed to save error history: {e}")

        # エラー通知
        self._send_error_notification(error_message)

        return result
