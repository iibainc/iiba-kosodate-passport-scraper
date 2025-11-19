"""Firestoreクライアント"""
import os
from typing import Any, Optional

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from ....shared.exceptions.errors import StorageError
from ....shared.logging.config import get_logger

logger = get_logger(__name__)


class FirestoreClient:
    """Firestore操作クライアント"""

    def __init__(self, project_id: str, database_id: str = "(default)") -> None:
        """
        Firestoreクライアントを初期化

        Args:
            project_id: GCPプロジェクトID
            database_id: データベースID（デフォルトは"(default)"）
        """
        self.project_id = project_id
        self.database_id = database_id

        # エミュレータモードの検出
        emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST")

        try:
            self.client = firestore.Client(
                project=project_id, database=database_id
            )

            if emulator_host:
                logger.info(
                    f"Firestore client initialized (EMULATOR MODE): "
                    f"host={emulator_host}, project={project_id}, database={database_id}"
                )
            else:
                logger.info(
                    f"Firestore client initialized: project={project_id}, database={database_id}"
                )
        except Exception as e:
            raise StorageError(f"Failed to initialize Firestore client: {e}") from e

    def get_collection(self, collection_path: str) -> firestore.CollectionReference:
        """
        コレクション参照を取得

        Args:
            collection_path: コレクションパス

        Returns:
            CollectionReference: コレクション参照
        """
        return self.client.collection(collection_path)

    def batch_write(
        self,
        collection_path: str,
        documents: list[dict[str, Any]],
        batch_size: int = 500,
        id_field: str = "shop_id",
    ) -> None:
        """
        バッチ書き込み（500件ずつ）

        Args:
            collection_path: コレクションパス
            documents: 書き込むドキュメントのリスト
            batch_size: バッチサイズ（デフォルト500、最大500）
            id_field: ドキュメントIDとして使用するフィールド名

        Raises:
            StorageError: 書き込みに失敗した場合
        """
        if batch_size > 500:
            raise ValueError("Batch size must be <= 500")

        if not documents:
            logger.info("No documents to write")
            return

        collection = self.get_collection(collection_path)
        total = len(documents)
        written = 0

        try:
            for i in range(0, total, batch_size):
                batch = self.client.batch()
                chunk = documents[i : i + batch_size]

                for doc in chunk:
                    doc_id = doc.get(id_field)
                    if not doc_id:
                        logger.warning(
                            f"Document missing {id_field}, skipping: {doc}"
                        )
                        continue

                    doc_ref = collection.document(str(doc_id))
                    batch.set(doc_ref, doc, merge=True)

                batch.commit()
                written += len(chunk)
                logger.info(
                    f"Batch write: {written}/{total} documents written to {collection_path}"
                )

            logger.info(
                f"Batch write completed: {written} documents written to {collection_path}"
            )

        except Exception as e:
            raise StorageError(
                f"Failed to batch write to {collection_path}: {e}"
            ) from e

    def get_document(
        self, collection_path: str, document_id: str
    ) -> Optional[dict[str, Any]]:
        """
        ドキュメントを取得

        Args:
            collection_path: コレクションパス
            document_id: ドキュメントID

        Returns:
            Optional[dict[str, Any]]: ドキュメントデータ（存在しない場合はNone）
        """
        try:
            doc_ref = self.get_collection(collection_path).document(document_id)
            doc = doc_ref.get()

            if doc.exists:
                return doc.to_dict()
            return None

        except Exception as e:
            raise StorageError(
                f"Failed to get document {document_id} from {collection_path}: {e}"
            ) from e

    def query_documents(
        self,
        collection_path: str,
        filters: Optional[list[tuple[str, str, Any]]] = None,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        条件に一致するドキュメントを取得

        Args:
            collection_path: コレクションパス
            filters: フィルタ条件のリスト [(field, operator, value), ...]
            limit: 取得件数の上限

        Returns:
            list[dict[str, Any]]: ドキュメントのリスト

        Example:
            >>> client.query_documents(
            ...     "shops",
            ...     filters=[("prefecture_code", "==", "08"), ("is_active", "==", True)],
            ...     limit=100
            ... )
        """
        try:
            query = self.get_collection(collection_path)

            if filters:
                for field, operator, value in filters:
                    query = query.where(filter=FieldFilter(field, operator, value))

            if limit:
                query = query.limit(limit)

            docs = query.stream()
            return [doc.to_dict() for doc in docs if doc.exists]

        except Exception as e:
            raise StorageError(
                f"Failed to query documents from {collection_path}: {e}"
            ) from e

    def delete_document(self, collection_path: str, document_id: str) -> None:
        """
        ドキュメントを削除

        Args:
            collection_path: コレクションパス
            document_id: ドキュメントID
        """
        try:
            doc_ref = self.get_collection(collection_path).document(document_id)
            doc_ref.delete()
            logger.info(f"Document {document_id} deleted from {collection_path}")

        except Exception as e:
            raise StorageError(
                f"Failed to delete document {document_id} from {collection_path}: {e}"
            ) from e

    def update_document(
        self, collection_path: str, document_id: str, updates: dict[str, Any]
    ) -> None:
        """
        ドキュメントを更新

        Args:
            collection_path: コレクションパス
            document_id: ドキュメントID
            updates: 更新内容
        """
        try:
            doc_ref = self.get_collection(collection_path).document(document_id)
            doc_ref.update(updates)
            logger.info(
                f"Document {document_id} updated in {collection_path}: {updates}"
            )

        except Exception as e:
            raise StorageError(
                f"Failed to update document {document_id} in {collection_path}: {e}"
            ) from e

    def count_documents(
        self,
        collection_path: str,
        filters: Optional[list[tuple[str, str, Any]]] = None,
    ) -> int:
        """
        ドキュメント数をカウント

        Args:
            collection_path: コレクションパス
            filters: フィルタ条件のリスト [(field, operator, value), ...]

        Returns:
            int: ドキュメント数
        """
        try:
            query = self.get_collection(collection_path)

            if filters:
                for field, operator, value in filters:
                    query = query.where(filter=FieldFilter(field, operator, value))

            # count()メソッドを使用（Firestore v2.11.0以降）
            agg_query = query.count()
            result = agg_query.get()
            count = result[0][0].value

            return count

        except Exception as e:
            raise StorageError(
                f"Failed to count documents in {collection_path}: {e}"
            ) from e
