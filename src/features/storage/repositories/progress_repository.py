"""スクレイピング進捗リポジトリ"""

from datetime import datetime
from typing import Optional

from ....shared.exceptions.errors import StorageError
from ....shared.logging.config import get_logger
from ..clients.firestore_client import FirestoreClient

logger = get_logger(__name__)


class ProgressRepository:
    """スクレイピング進捗のリポジトリ"""

    COLLECTION_NAME = "scraping_progress"

    def __init__(self, firestore_client: FirestoreClient) -> None:
        """
        ProgressRepositoryを初期化

        Args:
            firestore_client: Firestoreクライアント
        """
        self.client = firestore_client
        logger.info("ProgressRepository initialized")

    def save_progress(
        self,
        prefecture_code: str,
        completed_pages: list[int],
        total_shops_saved: int,
        last_shop_id: str,
    ) -> None:
        """
        進捗を保存

        Args:
            prefecture_code: 都道府県コード
            completed_pages: 完了済みページリスト
            total_shops_saved: 保存済み店舗数
            last_shop_id: 最後に処理した店舗ID
        """
        try:
            collection = self.client.get_collection(self.COLLECTION_NAME)
            doc_ref = collection.document(prefecture_code)

            progress_data = {
                "prefecture_code": prefecture_code,
                "completed_pages": completed_pages,
                "total_shops_saved": total_shops_saved,
                "last_shop_id": last_shop_id,
                "updated_at": datetime.now(),
            }

            doc_ref.set(progress_data)
            logger.info(
                f"Progress saved: {prefecture_code}, pages={len(completed_pages)}, shops={total_shops_saved}"
            )

        except Exception as e:
            logger.error(f"Failed to save progress: {e}")
            raise StorageError(f"Failed to save progress: {e}") from e

    def get_progress(self, prefecture_code: str) -> Optional[dict]:
        """
        進捗を取得

        Args:
            prefecture_code: 都道府県コード

        Returns:
            Optional[dict]: 進捗データ（存在しない場合はNone）
        """
        try:
            collection = self.client.get_collection(self.COLLECTION_NAME)
            doc_ref = collection.document(prefecture_code)
            doc = doc_ref.get()

            if doc.exists:
                progress = doc.to_dict()
                logger.info(
                    f"Progress loaded: {prefecture_code}, pages={len(progress.get('completed_pages', []))}"
                )
                return progress
            else:
                logger.info(f"No progress found for {prefecture_code}")
                return None

        except Exception as e:
            logger.error(f"Failed to get progress: {e}")
            return None

    def clear_progress(self, prefecture_code: str) -> None:
        """
        進捗をクリア（完了時）

        Args:
            prefecture_code: 都道府県コード
        """
        try:
            collection = self.client.get_collection(self.COLLECTION_NAME)
            doc_ref = collection.document(prefecture_code)
            doc_ref.delete()
            logger.info(f"Progress cleared: {prefecture_code}")

        except Exception as e:
            logger.error(f"Failed to clear progress: {e}")
