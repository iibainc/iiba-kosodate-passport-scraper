"""奈良県の店舗情報パーサー"""

from datetime import datetime
from typing import Any, Optional

from .....shared.logging.config import get_logger
from ...domain.models import Shop
from ..base import BaseParser

logger = get_logger(__name__)


class NaraParser(BaseParser):
    """
    奈良県の店舗情報パーサー
    APIレスポンス（JSON）から店舗情報を抽出する
    """

    def __init__(self, prefecture_code: str = "29", prefecture_name: str = "奈良県") -> None:
        """
        Args:
            prefecture_code: 都道府県コード
            prefecture_name: 都道府県名
        """
        super().__init__()
        self.prefecture_code = prefecture_code
        self.prefecture_name = prefecture_name

    def parse(self, html: str, url: str, shop_id: str) -> Optional[Shop]:
        """
        HTMLをパースして店舗情報を抽出
        (NaraScraperでは使用しないが、BaseParserの要件として実装)
        """
        logger.warning("NaraParser.parse() is not used. Use parse_shop_detail() instead.")
        return None

    def parse_shop_detail(self, data: dict[str, Any]) -> Optional[Shop]:
        """
        APIレスポンス（詳細情報）からShopオブジェクトを作成

        Args:
            data: APIからの詳細データ (returnValue)

        Returns:
            Optional[Shop]: 店舗オブジェクト
        """
        try:
            original_id = data.get("Id")
            if not original_id:
                logger.warning("Shop ID not found in data")
                return None

            # shop_idを生成 (例: 29_a045i00000KbS55AAF)
            # ShopRepositoryのバリデーション (prefecture_code_number) に合わせるため
            shop_id = f"{self.prefecture_code}_{original_id}"

            name = data.get("Name", "")
            
            # 住所の構築
            state = data.get("State__c", "")
            city = data.get("City__c", "")
            street = data.get("Street__c", "")
            building = data.get("BldgName_RoomNum__c", "")
            
            address = f"{state}{city}{street}"
            if building:
                address += f" {building}"
            
            # Postal Code
            postal_code = data.get("PostalCode__c", "")
            if postal_code and "-" not in postal_code and len(postal_code) == 7:
                postal_code = f"{postal_code[:3]}-{postal_code[3:]}"

            # Shop Object
            shop = Shop(
                shop_id=shop_id,
                prefecture_code=self.prefecture_code,
                prefecture_name=self.prefecture_name,
                name=name,
                address=address,
                phone=data.get("TelephoneNumber__c"),
                postal_code=postal_code,
                business_hours=None,  # APIデータには含まれていない模様
                closed_days=None,     # APIデータには含まれていない模様
                detail_url=f"https://nsa.pref.nara.jp/ctz/baseDetail?id={original_id}",
                website=data.get("URL__c"),
                benefits=data.get("BenefitsContent__c"),
                description=data.get("StoreIntroductions__c"),
                parking=None,
                category=data.get("StoreServiceCategory__c"), # 例: "割引;プレゼント"
                genre=data.get("StoreGenre__c"),             # 例: "飲食;お買い物"
                scraped_at=datetime.now(),
                updated_at=datetime.now(),
                is_active=data.get("IsPublic__c", True),
            )
            
            # その他フィールド
            shop.extra_fields["original_id"] = original_id
            shop.extra_fields["IsPapas"] = data.get("IsPapas__c")
            shop.extra_fields["RaisingChildrenUsedService"] = data.get("RaisingChildrenUsedService__c")
            
            return shop

        except Exception as e:
            logger.error(f"Failed to parse shop detail data: {e}")
            return None