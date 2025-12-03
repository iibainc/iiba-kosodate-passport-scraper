"""大阪府パーサー"""

from typing import Any, Optional

from .....shared.exceptions.errors import ParsingError
from .....shared.logging.config import get_logger
from .....shared.utils.text import extract_phone_number, extract_postal_code, normalize_text
from ...domain.models import Shop

logger = get_logger(__name__)


class OsakaParser:
    """
    大阪府の店舗情報パーサー

    APIから返却されるJSONデータをShopオブジェクトに変換します。
    """

    def __init__(self, prefecture_code: str, prefecture_name: str) -> None:
        """
        Args:
            prefecture_code: 都道府県コード（"27"）
            prefecture_name: 都道府県名（"大阪府"）
        """
        self.prefecture_code = prefecture_code
        self.prefecture_name = prefecture_name

    def parse(self, data: dict[str, Any]) -> Optional[Shop]:
        """
        JSONデータから店舗情報を抽出

        Args:
            data: 店舗情報の辞書（APIレスポンスの1レコード）

        Returns:
            Optional[Shop]: 店舗オブジェクト（パース失敗時はNone）

        Raises:
            ParsingError: パース失敗時
        """
        try:
            # 必須フィールドの確認
            shop_id = str(data.get("SHOPID", ""))
            if not shop_id:
                logger.warning("Shop ID not found in data")
                return None

            name = normalize_text(data.get("SHOPNAME", ""))
            if not name:
                logger.warning(f"Shop name not found: {shop_id}")
                return None

            # 基本情報の抽出
            address = normalize_text(data.get("JUSHO", ""))
            phone = extract_phone_number(data.get("TEL", ""))

            # 郵便番号
            postal_code = data.get("YUBINNO", "")
            if postal_code == "0":
                postal_code = None
            if not postal_code and address:
                postal_code = extract_postal_code(address)

            # 優待内容
            benefits_title = normalize_text(data.get("TOKUTENTITLE", ""))
            benefits_detail = normalize_text(data.get("TOKUTENDETAIL", ""))
            benefits = f"{benefits_title}\n{benefits_detail}".strip()

            # 紹介文
            description = normalize_text(data.get("COMMENT", ""))

            # ウェブサイト（COMMENTから抽出するか、専用フィールドがあれば使うが、現状はCOMMENTに含まれることが多い）
            # 簡易的な抽出
            website = None
            if description and "http" in description:
                import re

                url_match = re.search(r"https?://[\w/:%#\$&\?\(\)~\.=\+\-]+", description)
                if url_match:
                    website = url_match.group(0)

            # 営業時間・定休日（APIレスポンスには明確なフィールドが見当たらないため、COMMENTや詳細から探すか、Noneとする）
            # 現状のサンプルデータには含まれていないためNone
            business_hours = None
            closed_days = None

            # 座標
            latitude = None
            longitude = None
            try:
                lat_str = data.get("IDO")
                lon_str = data.get("KEDO")
                if lat_str and lon_str:
                    latitude = float(lat_str)
                    longitude = float(lon_str)
            except (ValueError, TypeError):
                pass

            # 詳細URL（公式サイトの店舗詳細ページ）
            # chain店か個人店かでURLが変わるロジックがJSにあったが、ここではシンプルにIDベースで生成
            # JSロジック:
            # if(CHAINFLG=="0") URL = .../private/?page=ID
            # if(CHAINFLG=="1") URL = .../chain/?page=ID
            chain_flg = data.get("CHAINFLG", "0")
            base_detail_url = "https://osaka-pass.jp/maidoko/kaiin/joken/kekka"
            if chain_flg == "1":
                detail_url = f"{base_detail_url}/chain/?page={shop_id}"
            else:
                detail_url = f"{base_detail_url}/private/?page={shop_id}"

            # Shopオブジェクトの作成
            shop = Shop(
                shop_id=f"{self.prefecture_code}_{shop_id}",  # ユニークにするためプレフィックス付与
                prefecture_code=self.prefecture_code,
                prefecture_name=self.prefecture_name,
                name=name,
                address=address,
                phone=phone,
                business_hours=business_hours,
                closed_days=closed_days,
                detail_url=detail_url,
                website=website,
                benefits=benefits,
                description=description,
                parking=None,  # 情報なし
                postal_code=postal_code,
                latitude=latitude,
                longitude=longitude,
            )

            # 検索用キーワードを生成
            shop.generate_search_terms()

            return shop

        except Exception as e:
            raise ParsingError(f"Failed to parse shop data: {e}") from e
