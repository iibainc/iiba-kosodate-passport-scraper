"""ジオコーディング機能のドメインモデル"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class GeoLocation:
    """地理的位置情報"""

    latitude: float  # 緯度
    longitude: float  # 経度
    formatted_address: Optional[str] = None  # 正規化された住所
    place_id: Optional[str] = None  # Google Maps Place ID（オプション）

    def __repr__(self) -> str:
        return f"GeoLocation(lat={self.latitude}, lng={self.longitude})"

    def to_tuple(self) -> tuple[float, float]:
        """(緯度, 経度)のタプルとして返す"""
        return (self.latitude, self.longitude)
