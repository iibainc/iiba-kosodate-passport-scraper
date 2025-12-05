"""兵庫県の店舗情報パーサー"""

import json
from datetime import datetime
from typing import Any, Optional

from .....shared.logging.config import get_logger
from ...domain.models import Shop
from ..base import BaseParser

logger = get_logger(__name__)


class HyogoParser(BaseParser):
    """兵庫県の店舗情報パーサー"""

    def __init__(self, prefecture_code: str = "28", prefecture_name: str = "兵庫県") -> None:
        """
        Args:
            prefecture_code: 都道府県コード
            prefecture_name: 都道府県名
        """
        super().__init__()
        self.prefecture_code = prefecture_code
        self.prefecture_name = prefecture_name

    def parse(self, item: dict[str, Any], url: str) -> Optional[Shop]:
        """
        APIレスポンスのアイテムをパースして店舗情報を抽出

        Args:
            item: APIレスポンスのアイテム（辞書）
            url: 店舗詳細URL（生成されたもの）

        Returns:
            Optional[Shop]: 店舗オブジェクト（パース失敗時はNone）
        """
        try:
            item_id = item.get("item_id")
            shop_name = item.get("item_name")

            if not item_id or not shop_name:
                logger.warning(f"Missing required fields: item_id={item_id}, name={shop_name}")
                return None

            # shop_idを都道府県コード付きの形式に変換（例: "28_LND0000270"）
            shop_id = f"{self.prefecture_code}_{item_id}"

            # explanationフィールドはJSON文字列なのでパースする
            explanation_str = item.get("explanation", "{}")
            explanation = {}
            try:
                if explanation_str:
                    explanation = json.loads(explanation_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse explanation JSON for {shop_id}")

            # 住所
            address = item.get("address", "")
            
            # 郵便番号
            postal_code = item.get("zip_code", "")

            # 電話番号
            phone = item.get("tel", "")

            # 営業時間
            business_hours = item.get("businesshours", "")

            # 定休日
            closed_days = item.get("holiday_other", "")

            # Webサイト
            website = item.get("url", "")

            # 緯度経度
            latitude = item.get("spot_position_lat")
            longitude = item.get("spot_position_lng")

            # 特典内容の構築
            benefits = []
            for i in range(1, 4):
                option = explanation.get(f"option{i}")
                if option:
                    benefits.append(option)
            benefits_str = "\n".join(benefits)

            # 店舗オブジェクトを作成
            shop = Shop(
                shop_id=shop_id,
                prefecture_code=self.prefecture_code,
                prefecture_name=self.prefecture_name,
                name=shop_name,
                address=address,
                phone=phone,
                postal_code=postal_code,
                business_hours=business_hours,
                closed_days=closed_days,
                detail_url=url,
                website=website,
                benefits=benefits_str,
                description=item.get("memo", ""),
                parking=None,  # APIには駐車場情報が明確にない
                category=None, # カテゴリはIDで返ってくるがマッピングが必要（今回は省略）
                genre=None,
                latitude=float(latitude) if latitude is not None else None,
                longitude=float(longitude) if longitude is not None else None,
                scraped_at=datetime.now(),
                updated_at=datetime.now(),
                is_active=True,
            )

            # その他のフィールドをextra_fieldsに保存
            shop.extra_fields["yomi"] = item.get("yomi", "")
            shop.extra_fields["areas"] = item.get("areas", [])
            shop.extra_fields["categories"] = item.get("categories", [])
            shop.extra_fields["explanation"] = explanation

            return shop

        except Exception as e:
            logger.error(f"Failed to parse shop item: {item.get('item_id')} - {e}")
            return None
