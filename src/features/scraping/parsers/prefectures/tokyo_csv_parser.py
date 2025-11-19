"""東京都CSVパーサー"""
import csv
import hashlib
from typing import Optional

from ...domain.models import Shop
from .....shared.exceptions.errors import ParsingError
from .....shared.logging.config import get_logger
from .....shared.utils.text import normalize_text, extract_phone, extract_postal_code

logger = get_logger(__name__)


class TokyoCsvParser:
    """
    東京都のCSVデータをShopオブジェクトに変換するパーサー

    CSVファイルの各行を解析して、Shopモデルに変換します。
    """

    def __init__(self, prefecture_code: str, prefecture_name: str, column_mapping: dict):
        """
        Args:
            prefecture_code: 都道府県コード（例: "13"）
            prefecture_name: 都道府県名（例: "東京都"）
            column_mapping: CSVカラムのインデックスマッピング
        """
        self.prefecture_code = prefecture_code
        self.prefecture_name = prefecture_name
        self.columns = column_mapping

    def parse_row(self, row: list[str]) -> Optional[Shop]:
        """
        CSV行をShopオブジェクトに変換

        Args:
            row: CSV行データ（リスト）

        Returns:
            Optional[Shop]: 変換されたShopオブジェクト（失敗時はNone）
        """
        try:
            # 必須フィールドのチェック
            if len(row) <= max(self.columns.values()):
                logger.warning(f"Row has insufficient columns: {len(row)} columns")
                return None

            # 店舗名取得（必須）
            name = self._get_value(row, "name")
            if not name or name.strip() == "":
                logger.warning("Shop name is empty, skipping")
                return None

            # 基本情報
            shop_id_str = self._get_value(row, "shop_id")
            postal_code = self._get_value(row, "postal_code")
            city = self._get_value(row, "city")
            address1 = self._get_value(row, "address1")
            address2 = self._get_value(row, "address2")

            # 住所を結合
            address_parts = []
            if self.prefecture_name:
                address_parts.append(self.prefecture_name)
            if city:
                address_parts.append(city)
            if address1:
                address_parts.append(address1)
            if address2:
                address_parts.append(address2)

            address = "".join(address_parts)

            # 連絡先情報
            phone = self._get_value(row, "phone")
            website = self._get_value(row, "website")

            # 営業情報
            business_hours = self._get_value(row, "business_hours")
            closed_days = self._get_value(row, "closed_days")
            parking = self._get_value(row, "parking")

            # 業種情報
            genres = []
            for genre_key in ["genre1", "genre2", "genre3"]:
                genre = self._get_value(row, genre_key)
                if genre:
                    genres.append(genre)
            genre_detail = self._get_value(row, "genre_detail")

            # 優待内容を構築
            benefits = self._build_benefits(row)

            # 説明文を構築（業種 + サービス概要）
            description_parts = []
            if genres:
                description_parts.append(f"業種: {', '.join(genres)}")
            if genre_detail:
                description_parts.append(f"({genre_detail})")

            description = " ".join(description_parts) if description_parts else None

            # Shop IDを生成（CSV のshop_idを使用、なければ名前+住所でハッシュ生成）
            if shop_id_str:
                shop_id = f"{self.prefecture_code}_{shop_id_str}"
            else:
                # フォールバック: 名前+住所でハッシュ生成
                unique_str = f"{name}{address}"
                hash_value = hashlib.sha256(unique_str.encode("utf-8")).hexdigest()[:8]
                shop_id = f"{self.prefecture_code}_{hash_value}"

            # Shopオブジェクト作成
            shop = Shop(
                shop_id=shop_id,
                prefecture_code=self.prefecture_code,
                prefecture_name=self.prefecture_name,
                name=normalize_text(name),
                address=normalize_text(address) if address else None,
                phone=extract_phone(phone) if phone else None,
                business_hours=normalize_text(business_hours) if business_hours else None,
                closed_days=normalize_text(closed_days) if closed_days else None,
                detail_url=website if website else None,
                website=website if website else None,
                benefits=normalize_text(benefits) if benefits else None,
                description=normalize_text(description) if description else None,
                parking=normalize_text(parking) if parking else None,
            )

            return shop

        except Exception as e:
            logger.error(f"Failed to parse CSV row: {e}")
            raise ParsingError(f"CSV parsing failed: {e}") from e

    def _get_value(self, row: list[str], key: str) -> Optional[str]:
        """
        列マッピングから値を取得

        Args:
            row: CSV行データ
            key: 列キー（例: "name", "address1"）

        Returns:
            Optional[str]: 取得した値（存在しない場合はNone）
        """
        try:
            if key not in self.columns:
                return None

            index = self.columns[key]
            if index >= len(row):
                return None

            value = row[index].strip()
            return value if value else None
        except Exception:
            return None

    def _build_benefits(self, row: list[str]) -> Optional[str]:
        """
        優待内容を構築

        Args:
            row: CSV行データ

        Returns:
            Optional[str]: 優待内容の説明文
        """
        benefits = []

        # サービス内容（○がついているもの）
        services = {
            "service_milk": "粉ミルクのお湯の提供",
            "service_diaper": "おむつ替えスペースあり",
            "service_baby_keep": "トイレにベビーキープ設置",
            "service_nursing": "授乳スペースあり",
            "service_kids_space": "キッズスペースあり",
            "service_stroller": "ベビーカー入店可能",
            "service_gift": "景品の提供",
            "service_points": "ポイントの付与",
            "service_discount": "商品の割引",
        }

        for key, label in services.items():
            value = self._get_value(row, key)
            if value and value == "○":
                benefits.append(label)

        # 割引の詳細があれば追加
        discount_detail = self._get_value(row, "discount_detail")
        if discount_detail:
            benefits.append(f"詳細: {discount_detail}")

        return "、".join(benefits) if benefits else None
