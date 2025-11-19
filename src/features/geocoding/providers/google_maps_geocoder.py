"""Google Maps Geocoding API実装"""
from typing import Optional

import googlemaps

from ..domain.models import GeoLocation
from ....shared.exceptions.errors import GeocodingError
from ....shared.logging.config import get_logger

logger = get_logger(__name__)


class GoogleMapsGeocoder:
    """Google Maps Geocoding API実装"""

    def __init__(self, api_key: str) -> None:
        """
        Args:
            api_key: Google Maps API キー
        """
        try:
            self.client = googlemaps.Client(key=api_key)
            logger.info("GoogleMapsGeocoder initialized")
        except Exception as e:
            raise GeocodingError(f"Failed to initialize Google Maps client: {e}") from e

    def geocode(self, address: str, region: str = "jp") -> Optional[GeoLocation]:
        """
        住所をジオコーディング

        Args:
            address: 住所文字列
            region: 地域バイアス（デフォルト: "jp"）

        Returns:
            Optional[GeoLocation]: 地理的位置情報（見つからない場合はNone）

        Raises:
            GeocodingError: APIリクエストに失敗した場合
        """
        if not address:
            logger.warning("Empty address provided for geocoding")
            return None

        try:
            logger.debug(f"Geocoding address: {address}")

            # Google Maps Geocoding APIを呼び出し
            results = self.client.geocode(address, region=region)

            if not results:
                logger.warning(f"No geocoding results for address: {address}")
                return None

            # 最初の結果を使用
            result = results[0]
            geometry = result.get("geometry", {})
            location = geometry.get("location", {})

            latitude = location.get("lat")
            longitude = location.get("lng")

            if latitude is None or longitude is None:
                logger.warning(
                    f"Invalid geocoding result (missing lat/lng): {address}"
                )
                return None

            formatted_address = result.get("formatted_address")
            place_id = result.get("place_id")

            geo_location = GeoLocation(
                latitude=latitude,
                longitude=longitude,
                formatted_address=formatted_address,
                place_id=place_id,
            )

            logger.debug(
                f"Geocoded: {address} -> ({latitude}, {longitude})"
            )

            return geo_location

        except googlemaps.exceptions.ApiError as e:
            raise GeocodingError(f"Google Maps API error: {e}") from e
        except googlemaps.exceptions.TransportError as e:
            raise GeocodingError(f"Google Maps transport error: {e}") from e
        except Exception as e:
            raise GeocodingError(
                f"Unexpected error during geocoding: {e}"
            ) from e

    def reverse_geocode(
        self, latitude: float, longitude: float
    ) -> Optional[GeoLocation]:
        """
        座標から住所を取得（逆ジオコーディング）

        Args:
            latitude: 緯度
            longitude: 経度

        Returns:
            Optional[GeoLocation]: 地理的位置情報（見つからない場合はNone）

        Raises:
            GeocodingError: APIリクエストに失敗した場合
        """
        try:
            logger.debug(f"Reverse geocoding: ({latitude}, {longitude})")

            # Google Maps Reverse Geocoding APIを呼び出し
            results = self.client.reverse_geocode((latitude, longitude))

            if not results:
                logger.warning(
                    f"No reverse geocoding results for: ({latitude}, {longitude})"
                )
                return None

            # 最初の結果を使用
            result = results[0]
            formatted_address = result.get("formatted_address")
            place_id = result.get("place_id")

            geo_location = GeoLocation(
                latitude=latitude,
                longitude=longitude,
                formatted_address=formatted_address,
                place_id=place_id,
            )

            logger.debug(
                f"Reverse geocoded: ({latitude}, {longitude}) -> {formatted_address}"
            )

            return geo_location

        except googlemaps.exceptions.ApiError as e:
            raise GeocodingError(f"Google Maps API error: {e}") from e
        except googlemaps.exceptions.TransportError as e:
            raise GeocodingError(f"Google Maps transport error: {e}") from e
        except Exception as e:
            raise GeocodingError(
                f"Unexpected error during reverse geocoding: {e}"
            ) from e
