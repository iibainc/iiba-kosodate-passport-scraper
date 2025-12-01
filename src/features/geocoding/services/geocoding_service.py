"""ジオコーディングサービス"""

import time
from typing import Optional

from tqdm import tqdm

from ...scraping.domain.models import Shop
from ..domain.models import GeoLocation
from ....shared.exceptions.errors import GeocodingError
from ....shared.logging.config import get_logger
from ..providers.cache_geocoder import CacheGeocoder
from ..providers.google_maps_geocoder import GoogleMapsGeocoder

logger = get_logger(__name__)


class GeocodingService:
    """ジオコーディングサービス"""

    def __init__(
        self,
        api_key: str,
        use_cache: bool = True,
        delay_between_requests: float = 0.1,
    ) -> None:
        """
        Args:
            api_key: Google Maps API キー
            use_cache: キャッシュを使用するか
            delay_between_requests: リクエスト間の遅延（秒）
        """
        self.base_geocoder = GoogleMapsGeocoder(api_key)

        if use_cache:
            self.geocoder: CacheGeocoder | GoogleMapsGeocoder = CacheGeocoder(self.base_geocoder)
        else:
            self.geocoder = self.base_geocoder

        self.delay_between_requests = delay_between_requests

        logger.info(
            f"GeocodingService initialized: cache={use_cache}, delay={delay_between_requests}s"
        )

    def geocode_shop(self, shop: Shop) -> bool:
        """
        店舗の住所をジオコーディングし、緯度・経度を設定

        Args:
            shop: 店舗オブジェクト

        Returns:
            bool: 成功した場合True、失敗した場合False
        """
        if not shop.address:
            logger.debug(f"Shop {shop.shop_id} has no address, skipping geocoding")
            return False

        try:
            # 住所に都道府県名を追加（精度向上のため）
            full_address = f"{shop.prefecture_name}{shop.address}"

            geo_location = self.geocoder.geocode(full_address)

            if geo_location:
                shop.latitude = geo_location.latitude
                shop.longitude = geo_location.longitude

                from datetime import datetime

                shop.geocoded_at = datetime.now()

                logger.debug(
                    f"Geocoded shop {shop.shop_id}: {full_address} -> ({geo_location.latitude}, {geo_location.longitude})"
                )
                return True
            else:
                logger.warning(f"Failed to geocode shop {shop.shop_id}: {full_address}")
                return False

        except GeocodingError as e:
            logger.error(f"Geocoding error for shop {shop.shop_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during geocoding for shop {shop.shop_id}: {e}")
            return False

    def geocode_shops_batch(self, shops: list[Shop], show_progress: bool = True) -> dict[str, int]:
        """
        複数の店舗をバッチジオコーディング

        Args:
            shops: 店舗オブジェクトのリスト
            show_progress: プログレスバーを表示するか

        Returns:
            dict[str, int]: ジオコーディング結果（成功数、失敗数）
        """
        success_count = 0
        failure_count = 0
        skipped_count = 0

        logger.info(f"Starting batch geocoding: {len(shops)} shops")

        # プログレスバーを使用してバッチ処理
        iterator = tqdm(shops, desc="ジオコーディング") if show_progress else shops

        for shop in iterator:
            # 既にジオコーディング済みの場合はスキップ
            if shop.latitude is not None and shop.longitude is not None:
                skipped_count += 1
                continue

            # ジオコーディング実行
            success = self.geocode_shop(shop)

            if success:
                success_count += 1
            else:
                failure_count += 1

            # レート制限のため遅延
            if self.delay_between_requests > 0:
                time.sleep(self.delay_between_requests)

        result = {
            "success": success_count,
            "failure": failure_count,
            "skipped": skipped_count,
            "total": len(shops),
        }

        logger.info(
            f"Batch geocoding completed: {success_count} success, "
            f"{failure_count} failure, {skipped_count} skipped"
        )

        return result

    def prefetch_addresses(self, shops: list[Shop]) -> None:
        """
        店舗の住所を事前にキャッシュ（CacheGeocoderを使用している場合のみ）

        Args:
            shops: 店舗オブジェクトのリスト
        """
        if not isinstance(self.geocoder, CacheGeocoder):
            logger.warning("Prefetch is only supported when using CacheGeocoder")
            return

        # 住所のリストを作成
        addresses = []
        for shop in shops:
            if shop.address:
                full_address = f"{shop.prefecture_name}{shop.address}"
                addresses.append(full_address)

        # キャッシュに事前ロード
        self.geocoder.prefetch_addresses(addresses)

    def get_cache_stats(self) -> Optional[dict[str, int]]:
        """
        キャッシュ統計を取得（CacheGeocoderを使用している場合のみ）

        Returns:
            Optional[dict[str, int]]: キャッシュ統計
        """
        if isinstance(self.geocoder, CacheGeocoder):
            return self.geocoder.get_cache_stats()
        else:
            logger.warning("Cache stats are only available when using CacheGeocoder")
            return None

    def clear_cache(self) -> None:
        """キャッシュをクリア（CacheGeocoderを使用している場合のみ）"""
        if isinstance(self.geocoder, CacheGeocoder):
            self.geocoder.clear_cache()
        else:
            logger.warning("Cache clearing is only supported when using CacheGeocoder")
