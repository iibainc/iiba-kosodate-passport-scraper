"""店舗リポジトリ"""
from datetime import datetime
from typing import Any, Optional

from ...scraping.domain.models import Shop
from ....shared.exceptions.errors import StorageError, ValidationError
from ....shared.logging.config import get_logger
from ..clients.firestore_client import FirestoreClient

logger = get_logger(__name__)


class ShopRepository:
    """店舗データのリポジトリ"""

    COLLECTION_NAME = "kosodate_passport_shops"

    def __init__(self, firestore_client: FirestoreClient) -> None:
        """
        ShopRepositoryを初期化

        Args:
            firestore_client: Firestoreクライアント
        """
        self.client = firestore_client
        logger.info("ShopRepository initialized")

    def save(self, shop: Shop) -> None:
        """
        店舗を保存（新規作成または更新）

        Args:
            shop: 店舗オブジェクト

        Raises:
            ValidationError: バリデーションエラー
            StorageError: 保存に失敗した場合
        """
        self._validate_shop(shop)

        try:
            # 更新日時を設定
            shop.updated_at = datetime.now()

            # Firestoreに保存
            shop_dict = shop.to_firestore_dict()
            collection = self.client.get_collection(self.COLLECTION_NAME)
            doc_ref = collection.document(shop.shop_id)

            # 既存ドキュメントの確認
            existing_doc = doc_ref.get()

            if existing_doc.exists:
                # 更新
                doc_ref.set(shop_dict, merge=True)
                logger.info(f"Shop updated: {shop.shop_id} - {shop.name}")
            else:
                # 新規作成
                doc_ref.set(shop_dict)
                logger.info(f"Shop created: {shop.shop_id} - {shop.name}")

        except ValidationError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to save shop {shop.shop_id}: {e}") from e

    def save_batch(self, shops: list[Shop]) -> dict[str, int]:
        """
        複数の店舗をバッチ保存

        Args:
            shops: 店舗オブジェクトのリスト

        Returns:
            dict[str, int]: 保存結果（新規作成数、更新数）

        Raises:
            StorageError: 保存に失敗した場合
        """
        if not shops:
            logger.info("No shops to save")
            return {"created": 0, "updated": 0}

        new_count = 0
        updated_count = 0

        try:
            # 既存店舗IDを取得
            existing_ids = self._get_existing_shop_ids(
                [shop.shop_id for shop in shops]
            )

            # 店舗をFirestore形式に変換
            shop_dicts = []
            for shop in shops:
                # バリデーション
                try:
                    self._validate_shop(shop)
                except ValidationError as e:
                    logger.warning(
                        f"Skipping invalid shop {shop.shop_id}: {e}"
                    )
                    continue

                # 更新日時を設定
                shop.updated_at = datetime.now()

                # カウント
                if shop.shop_id in existing_ids:
                    updated_count += 1
                else:
                    new_count += 1

                shop_dicts.append(shop.to_firestore_dict())

            # バッチ書き込み
            self.client.batch_write(
                self.COLLECTION_NAME, shop_dicts, id_field="shop_id"
            )

            logger.info(
                f"Batch save completed: {new_count} created, {updated_count} updated"
            )

            return {"created": new_count, "updated": updated_count}

        except Exception as e:
            raise StorageError(f"Failed to batch save shops: {e}") from e

    def get_by_id(self, shop_id: str) -> Optional[Shop]:
        """
        店舗IDで店舗を取得

        Args:
            shop_id: 店舗ID

        Returns:
            Optional[Shop]: 店舗オブジェクト（存在しない場合はNone）
        """
        try:
            doc_data = self.client.get_document(self.COLLECTION_NAME, shop_id)

            if doc_data:
                return Shop.from_firestore_dict(doc_data)
            return None

        except Exception as e:
            raise StorageError(f"Failed to get shop {shop_id}: {e}") from e

    def get_by_prefecture(
        self, prefecture_code: str, is_active: bool = True, limit: Optional[int] = None
    ) -> list[Shop]:
        """
        都道府県コードで店舗を取得

        Args:
            prefecture_code: 都道府県コード
            is_active: アクティブな店舗のみ取得するか
            limit: 取得件数の上限

        Returns:
            list[Shop]: 店舗オブジェクトのリスト
        """
        try:
            filters = [("prefecture_code", "==", prefecture_code)]

            if is_active:
                filters.append(("is_active", "==", True))

            docs = self.client.query_documents(
                self.COLLECTION_NAME, filters=filters, limit=limit
            )

            shops = [Shop.from_firestore_dict(doc) for doc in docs]
            logger.info(
                f"Retrieved {len(shops)} shops for prefecture {prefecture_code}"
            )

            return shops

        except Exception as e:
            raise StorageError(
                f"Failed to get shops for prefecture {prefecture_code}: {e}"
            ) from e

    def search_by_name(
        self, name: str, prefecture_code: Optional[str] = None, limit: int = 100
    ) -> list[Shop]:
        """
        店名で検索

        Args:
            name: 店名（部分一致）
            prefecture_code: 都道府県コード（Noneの場合は全国検索）
            limit: 取得件数の上限

        Returns:
            list[Shop]: 店舗オブジェクトのリスト

        Note:
            Firestoreの制限により、完全な部分一致検索はクライアント側でフィルタリング
        """
        try:
            filters = [("is_active", "==", True)]

            if prefecture_code:
                filters.append(("prefecture_code", "==", prefecture_code))

            # search_termsフィールドを使用した検索
            # （完全一致のみ、部分一致は後でクライアント側でフィルタリング）
            docs = self.client.query_documents(
                self.COLLECTION_NAME, filters=filters
            )

            # クライアント側で店名による部分一致フィルタリング
            shops = []
            for doc in docs:
                shop = Shop.from_firestore_dict(doc)
                if name.lower() in shop.name.lower():
                    shops.append(shop)
                    if len(shops) >= limit:
                        break

            logger.info(f"Found {len(shops)} shops matching name '{name}'")

            return shops

        except Exception as e:
            raise StorageError(f"Failed to search shops by name '{name}': {e}") from e

    def count_by_prefecture(self, prefecture_code: str, is_active: bool = True) -> int:
        """
        都道府県ごとの店舗数をカウント

        Args:
            prefecture_code: 都道府県コード
            is_active: アクティブな店舗のみカウントするか

        Returns:
            int: 店舗数
        """
        try:
            filters = [("prefecture_code", "==", prefecture_code)]

            if is_active:
                filters.append(("is_active", "==", True))

            count = self.client.count_documents(self.COLLECTION_NAME, filters=filters)
            logger.info(f"Prefecture {prefecture_code} has {count} shops")

            return count

        except Exception as e:
            raise StorageError(
                f"Failed to count shops for prefecture {prefecture_code}: {e}"
            ) from e

    def deactivate(self, shop_id: str) -> None:
        """
        店舗を無効化（論理削除）

        Args:
            shop_id: 店舗ID
        """
        try:
            updates = {"is_active": False, "updated_at": datetime.now()}
            self.client.update_document(self.COLLECTION_NAME, shop_id, updates)
            logger.info(f"Shop deactivated: {shop_id}")

        except Exception as e:
            raise StorageError(f"Failed to deactivate shop {shop_id}: {e}") from e

    def delete(self, shop_id: str) -> None:
        """
        店舗を削除（物理削除）

        Args:
            shop_id: 店舗ID

        Warning:
            通常は deactivate() を使用することを推奨
        """
        try:
            self.client.delete_document(self.COLLECTION_NAME, shop_id)
            logger.info(f"Shop deleted: {shop_id}")

        except Exception as e:
            raise StorageError(f"Failed to delete shop {shop_id}: {e}") from e

    def update_geocoding(
        self, shop_id: str, latitude: float, longitude: float
    ) -> None:
        """
        ジオコーディング情報を更新

        Args:
            shop_id: 店舗ID
            latitude: 緯度
            longitude: 経度
        """
        try:
            updates = {
                "latitude": latitude,
                "longitude": longitude,
                "geocoded_at": datetime.now(),
                "updated_at": datetime.now(),
            }
            self.client.update_document(self.COLLECTION_NAME, shop_id, updates)
            logger.info(
                f"Geocoding updated for shop {shop_id}: ({latitude}, {longitude})"
            )

        except Exception as e:
            raise StorageError(
                f"Failed to update geocoding for shop {shop_id}: {e}"
            ) from e

    def _validate_shop(self, shop: Shop) -> None:
        """
        店舗データのバリデーション

        Args:
            shop: 店舗オブジェクト

        Raises:
            ValidationError: バリデーションエラー
        """
        if not shop.shop_id:
            raise ValidationError("shop_id is required")

        if not shop.prefecture_code:
            raise ValidationError("prefecture_code is required")

        if not shop.name:
            raise ValidationError("name is required")

        # shop_idのフォーマット確認（例: "08_00001"）
        if "_" not in shop.shop_id:
            raise ValidationError(
                f"Invalid shop_id format: {shop.shop_id} (expected: <prefecture_code>_<number>)"
            )

    def _get_existing_shop_ids(self, shop_ids: list[str]) -> set[str]:
        """
        既存の店舗IDを取得

        Args:
            shop_ids: 確認する店舗IDのリスト

        Returns:
            set[str]: 既存の店舗IDのセット
        """
        existing_ids = set()

        try:
            for shop_id in shop_ids:
                doc = self.client.get_document(self.COLLECTION_NAME, shop_id)
                if doc:
                    existing_ids.add(shop_id)

            return existing_ids

        except Exception as e:
            logger.warning(f"Failed to get existing shop IDs: {e}")
            return set()
