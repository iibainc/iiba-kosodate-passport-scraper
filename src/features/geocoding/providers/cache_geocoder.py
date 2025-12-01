"""キャッシュ付きジオコーダー"""

from typing import Optional

from ....shared.logging.config import get_logger
from ..domain.models import GeoLocation
from .google_maps_geocoder import GoogleMapsGeocoder

logger = get_logger(__name__)


class CacheGeocoder:
    """
    キャッシュ付きジオコーダー

    重複する住所のAPI呼び出しを削減するため、
    メモリ内キャッシュを使用
    """

    def __init__(self, geocoder: GoogleMapsGeocoder) -> None:
        """
        Args:
            geocoder: ベースとなるジオコーダー
        """
        self.geocoder = geocoder
        self.cache: dict[str, Optional[GeoLocation]] = {}
        self.hit_count = 0
        self.miss_count = 0

        logger.info("CacheGeocoder initialized")

    def geocode(self, address: str, region: str = "jp") -> Optional[GeoLocation]:
        """
        住所をジオコーディング（キャッシュあり）

        Args:
            address: 住所文字列
            region: 地域バイアス（デフォルト: "jp"）

        Returns:
            Optional[GeoLocation]: 地理的位置情報（見つからない場合はNone）
        """
        if not address:
            return None

        # 正規化したアドレスをキーとして使用
        cache_key = self._normalize_address(address)

        # キャッシュヒットチェック
        if cache_key in self.cache:
            self.hit_count += 1
            logger.debug(f"Cache hit for address: {address}")
            return self.cache[cache_key]

        # キャッシュミス: API呼び出し
        self.miss_count += 1
        logger.debug(f"Cache miss for address: {address}")

        geo_location = self.geocoder.geocode(address, region=region)

        # 結果をキャッシュ
        self.cache[cache_key] = geo_location

        return geo_location

    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[GeoLocation]:
        """
        座標から住所を取得（逆ジオコーディング、キャッシュあり）

        Args:
            latitude: 緯度
            longitude: 経度

        Returns:
            Optional[GeoLocation]: 地理的位置情報（見つからない場合はNone）
        """
        # 座標をキーとして使用（小数点以下6桁で丸める）
        cache_key = f"{latitude:.6f},{longitude:.6f}"

        # キャッシュヒットチェック
        if cache_key in self.cache:
            self.hit_count += 1
            logger.debug(f"Cache hit for coordinates: ({latitude}, {longitude})")
            return self.cache[cache_key]

        # キャッシュミス: API呼び出し
        self.miss_count += 1
        logger.debug(f"Cache miss for coordinates: ({latitude}, {longitude})")

        geo_location = self.geocoder.reverse_geocode(latitude, longitude)

        # 結果をキャッシュ
        self.cache[cache_key] = geo_location

        return geo_location

    def clear_cache(self) -> None:
        """キャッシュをクリア"""
        cache_size = len(self.cache)
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0
        logger.info(f"Cache cleared: {cache_size} entries removed")

    def get_cache_stats(self) -> dict[str, int]:
        """
        キャッシュ統計を取得

        Returns:
            dict[str, int]: キャッシュ統計（サイズ、ヒット数、ミス数、ヒット率）
        """
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0.0

        stats = {
            "cache_size": len(self.cache),
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
        }

        logger.info(f"Cache stats: {stats}")

        return stats

    def _normalize_address(self, address: str) -> str:
        """
        住所を正規化してキャッシュキーとして使用

        Args:
            address: 住所文字列

        Returns:
            str: 正規化された住所
        """
        # 空白を除去し、小文字に変換
        normalized = address.strip().lower()

        # 全角スペースを半角に変換
        normalized = normalized.replace("　", " ")

        # 連続する空白を1つに
        import re

        normalized = re.sub(r"\s+", " ", normalized)

        return normalized

    def prefetch_addresses(self, addresses: list[str], region: str = "jp") -> None:
        """
        複数の住所を事前にキャッシュ

        Args:
            addresses: 住所のリスト
            region: 地域バイアス（デフォルト: "jp"）
        """
        # 重複を除去
        unique_addresses = list(set(addresses))

        logger.info(f"Prefetching {len(unique_addresses)} unique addresses")

        for address in unique_addresses:
            if address and self._normalize_address(address) not in self.cache:
                self.geocode(address, region=region)

        logger.info(f"Prefetch completed: {len(self.cache)} entries cached")
