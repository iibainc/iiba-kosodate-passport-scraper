"""スクレイピング履歴リポジトリ"""

from typing import Optional

from ....shared.exceptions.errors import StorageError
from ....shared.logging.config import get_logger
from ...scraping.domain.models import ScrapingResult
from ..clients.firestore_client import FirestoreClient

logger = get_logger(__name__)


class HistoryRepository:
    """スクレイピング履歴のリポジトリ"""

    COLLECTION_NAME = "scraping_history"

    def __init__(self, firestore_client: FirestoreClient) -> None:
        """
        HistoryRepositoryを初期化

        Args:
            firestore_client: Firestoreクライアント
        """
        self.client = firestore_client
        logger.info("HistoryRepository initialized")

    def save(self, result: ScrapingResult) -> None:
        """
        スクレイピング結果を保存

        Args:
            result: スクレイピング結果オブジェクト

        Raises:
            StorageError: 保存に失敗した場合
        """
        try:
            result_dict = result.to_firestore_dict()
            collection = self.client.get_collection(self.COLLECTION_NAME)
            doc_ref = collection.document(result.run_id)

            doc_ref.set(result_dict, merge=True)
            logger.info(
                f"Scraping result saved: {result.run_id} - {result.prefecture_name} - {result.status.value}"
            )

        except Exception as e:
            raise StorageError(f"Failed to save scraping result {result.run_id}: {e}") from e

    def get_by_run_id(self, run_id: str) -> Optional[ScrapingResult]:
        """
        実行IDでスクレイピング結果を取得

        Args:
            run_id: 実行ID

        Returns:
            Optional[ScrapingResult]: スクレイピング結果オブジェクト（存在しない場合はNone）
        """
        try:
            doc_data = self.client.get_document(self.COLLECTION_NAME, run_id)

            if doc_data:
                return self._from_firestore_dict(doc_data)
            return None

        except Exception as e:
            raise StorageError(f"Failed to get scraping result {run_id}: {e}") from e

    def get_latest_by_prefecture(self, prefecture_code: str) -> Optional[ScrapingResult]:
        """
        都道府県の最新のスクレイピング結果を取得

        Args:
            prefecture_code: 都道府県コード

        Returns:
            Optional[ScrapingResult]: スクレイピング結果オブジェクト（存在しない場合はNone）
        """
        try:
            # started_atで降順ソート（最新を取得）
            collection = self.client.get_collection(self.COLLECTION_NAME)
            query = (
                collection.where(
                    filter=collection._client._firestore_api.FieldFilter(
                        "prefecture_code", "==", prefecture_code
                    )
                )
                .order_by("started_at", direction="DESCENDING")
                .limit(1)
            )

            docs = list(query.stream())

            if docs and docs[0].exists:
                return self._from_firestore_dict(docs[0].to_dict())
            return None

        except Exception as e:
            raise StorageError(
                f"Failed to get latest scraping result for prefecture {prefecture_code}: {e}"
            ) from e

    def get_history_by_prefecture(
        self, prefecture_code: str, limit: int = 100
    ) -> list[ScrapingResult]:
        """
        都道府県のスクレイピング履歴を取得

        Args:
            prefecture_code: 都道府県コード
            limit: 取得件数の上限

        Returns:
            list[ScrapingResult]: スクレイピング結果のリスト（新しい順）
        """
        try:
            collection = self.client.get_collection(self.COLLECTION_NAME)
            query = (
                collection.where(
                    filter=collection._client._firestore_api.FieldFilter(
                        "prefecture_code", "==", prefecture_code
                    )
                )
                .order_by("started_at", direction="DESCENDING")
                .limit(limit)
            )

            docs = query.stream()
            results = [self._from_firestore_dict(doc.to_dict()) for doc in docs if doc.exists]

            logger.info(
                f"Retrieved {len(results)} scraping history records for prefecture {prefecture_code}"
            )

            return results

        except Exception as e:
            raise StorageError(
                f"Failed to get scraping history for prefecture {prefecture_code}: {e}"
            ) from e

    def get_recent_results(self, limit: int = 50) -> list[ScrapingResult]:
        """
        最近のスクレイピング結果を取得

        Args:
            limit: 取得件数の上限

        Returns:
            list[ScrapingResult]: スクレイピング結果のリスト（新しい順）
        """
        try:
            collection = self.client.get_collection(self.COLLECTION_NAME)
            query = collection.order_by("started_at", direction="DESCENDING").limit(limit)

            docs = query.stream()
            results = [self._from_firestore_dict(doc.to_dict()) for doc in docs if doc.exists]

            logger.info(f"Retrieved {len(results)} recent scraping results")

            return results

        except Exception as e:
            raise StorageError(f"Failed to get recent scraping results: {e}") from e

    def count_by_status(self, prefecture_code: Optional[str] = None) -> dict[str, int]:
        """
        ステータスごとのスクレイピング実行回数をカウント

        Args:
            prefecture_code: 都道府県コード（Noneの場合は全国）

        Returns:
            dict[str, int]: ステータスごとの実行回数
        """
        try:
            filters = []
            if prefecture_code:
                filters.append(("prefecture_code", "==", prefecture_code))

            # 全件取得してクライアント側でカウント
            # （Firestoreのgroup byは制限があるため）
            docs = self.client.query_documents(self.COLLECTION_NAME, filters=filters)

            status_counts: dict[str, int] = {}
            for doc in docs:
                status = doc.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1

            logger.info(f"Status counts: {status_counts}")

            return status_counts

        except Exception as e:
            raise StorageError(f"Failed to count by status: {e}") from e

    def delete(self, run_id: str) -> None:
        """
        スクレイピング結果を削除

        Args:
            run_id: 実行ID

        Warning:
            通常は削除せず、データを保持することを推奨
        """
        try:
            self.client.delete_document(self.COLLECTION_NAME, run_id)
            logger.info(f"Scraping result deleted: {run_id}")

        except Exception as e:
            raise StorageError(f"Failed to delete scraping result {run_id}: {e}") from e

    def _from_firestore_dict(self, data: dict) -> ScrapingResult:
        """
        Firestoreのデータからスクレイピング結果オブジェクトを生成

        Args:
            data: Firestoreのドキュメントデータ

        Returns:
            ScrapingResult: スクレイピング結果オブジェクト
        """
        from ...scraping.domain.enums import ScrapingStatus

        return ScrapingResult(
            run_id=data["run_id"],
            prefecture_code=data["prefecture_code"],
            prefecture_name=data["prefecture_name"],
            started_at=data["started_at"],
            completed_at=data.get("completed_at"),
            status=ScrapingStatus(data.get("status", "pending")),
            total_shops=data.get("total_shops", 0),
            new_shops=data.get("new_shops", 0),
            updated_shops=data.get("updated_shops", 0),
            geocoded_shops=data.get("geocoded_shops", 0),
            geocoding_errors=data.get("geocoding_errors", 0),
            errors=data.get("errors", []),
            duration_seconds=data.get("duration_seconds"),
        )
