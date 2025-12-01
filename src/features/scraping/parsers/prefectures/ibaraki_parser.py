"""茨城県の店舗情報パーサー"""

import re
from datetime import datetime
from typing import Any, Optional

from bs4 import BeautifulSoup

from .....shared.logging.config import get_logger
from .....shared.utils.text import (
    extract_phone_number,
    extract_postal_code,
    normalize_text,
)
from ...domain.models import Shop
from ..base import BaseParser

logger = get_logger(__name__)


class IbarakiParser(BaseParser):
    """茨城県の店舗情報パーサー"""

    # 除外する汎用タイトル
    GENERIC_TITLES = [
        "協賛店検索",
        "市町村を複数選択",
        "いばらきKids Club",
        "いばらき子育て家庭優待制度",
    ]

    # 店名のキー候補
    NAME_KEYS = [
        "店舗名",
        "協賛店名",
        "施設名",
        "施設・店舗名",
        "事業者名",
        "名称",
        "名称（屋号）",
        "屋号",
        "商号",
        "会社名",
        "店舗・事業所名",
    ]

    def __init__(self, prefecture_code: str = "08", prefecture_name: str = "茨城県") -> None:
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

        Args:
            html: HTML文字列
            url: ページURL
            shop_id: 店舗ID

        Returns:
            Optional[Shop]: 店舗オブジェクト（パース失敗時はNone）
        """
        try:
            soup = self.create_soup(html)

            # データを抽出
            data: dict[str, Any] = {}

            # 店名を抽出
            shop_name = self._extract_shop_name(soup)
            if not shop_name:
                logger.warning(f"Shop name not found: {url}")
                return None

            # テーブルデータを抽出
            table_data = self.extract_table_data(soup, "table")
            data.update(table_data)

            # 定義リストデータを抽出
            dl_data = self.extract_dl_data(soup, "dl")
            data.update(dl_data)

            # 店舗オブジェクトを構築
            shop = self._build_shop(shop_id, shop_name, data, url, soup)

            logger.debug(f"Parsed shop: {shop.name} ({shop.shop_id})")
            return shop

        except Exception as e:
            logger.error(f"Failed to parse shop detail: {url} - {e}")
            return None

    def _extract_shop_name(self, soup: BeautifulSoup) -> Optional[str]:
        """
        店名を抽出

        Args:
            soup: BeautifulSoupオブジェクト

        Returns:
            Optional[str]: 店名（見つからない場合はNone）
        """
        # h4, h1, h2などの見出しから探す
        for selector in ["h4", "h1", "h2", ".title", ".page-title", ".shop-name"]:
            element = soup.select_one(selector)
            if element:
                text = normalize_text(element.get_text())
                if text and all(generic not in text for generic in self.GENERIC_TITLES):
                    return text

        # titleタグから推定
        if soup.title:
            title_text = normalize_text(soup.title.get_text())
            if title_text:
                # 区切り記号の手前を取得
                guessed = (
                    title_text.split("｜")[0] if "｜" in title_text else title_text.split("|")[0]
                )
                if guessed and all(generic not in guessed for generic in self.GENERIC_TITLES):
                    return guessed

        return None

    def _build_shop(
        self,
        shop_id: str,
        shop_name: str,
        data: dict[str, str],
        url: str,
        soup: BeautifulSoup,
    ) -> Shop:
        """
        店舗オブジェクトを構築

        Args:
            shop_id: 店舗ID
            shop_name: 店名
            data: 抽出されたデータ
            url: ページURL
            soup: BeautifulSoupオブジェクト

        Returns:
            Shop: 店舗オブジェクト
        """
        # データから各フィールドを抽出
        address = self._extract_address(data, soup)
        phone = self._extract_phone(data, soup)
        postal_code = self._extract_postal_code(address)

        # 店舗オブジェクトを作成
        shop = Shop(
            shop_id=shop_id,
            prefecture_code=self.prefecture_code,
            prefecture_name=self.prefecture_name,
            name=shop_name,
            address=address,
            phone=phone,
            postal_code=postal_code,
            business_hours=self._extract_field(
                data, ["営業時間", "営業日時", "利用時間", "開館時間"]
            ),
            closed_days=self._extract_field(data, ["定休日", "休館日", "休業日"]),
            detail_url=url,
            website=self._extract_field(data, ["URL", "公式サイト", "ホームページ", "Webサイト"]),
            benefits=self._extract_field(
                data,
                [
                    "子育て優待内容",
                    "割引特典",
                    "優待内容",
                    "サービス内容",
                    "特典",
                    "割引内容",
                ],
            ),
            description=self._extract_field(
                data, ["紹介コメント", "備考", "コメント", "説明", "紹介文"]
            ),
            parking=self._extract_field(data, ["駐車場", "駐車スペース"]),
            category=self._extract_field(data, ["カテゴリ", "カテゴリー", "業種"]),
            genre=self._extract_field(data, ["ジャンル", "分類"]),
            scraped_at=datetime.now(),
            updated_at=datetime.now(),
            is_active=True,
        )

        # その他のフィールドをextra_fieldsに保存
        excluded_keys = {
            "店舗名",
            "協賛店名",
            "施設名",
            "住所",
            "所在地",
            "電話番号",
            "TEL",
            "Tel",
            "電話",
            "郵便番号",
            "営業時間",
            "定休日",
            "URL",
            "優待内容",
            "備考",
            "駐車場",
            "カテゴリ",
            "ジャンル",
        }

        for key, value in data.items():
            if key not in excluded_keys:
                shop.extra_fields[key] = value

        return shop

    def _extract_address(self, data: dict[str, str], soup: BeautifulSoup) -> Optional[str]:
        """住所を抽出"""
        # データから探す
        address = self._extract_field(data, ["住所", "所在地", "address"])
        if address:
            return address

        # 推定: 郵便番号パターンから探す
        text_all = normalize_text(soup.get_text(" "))
        if text_all:
            match = re.search(r"(〒?\d{3}-\d{4}[^ \n　]*)", text_all)
            if match:
                return match.group(1)

        return None

    def _extract_phone(self, data: dict[str, str], soup: BeautifulSoup) -> Optional[str]:
        """電話番号を抽出"""
        # データから探す
        phone = self._extract_field(data, ["電話番号", "TEL", "Tel", "電話", "phone"])
        if phone:
            return phone

        # 推定: 電話番号パターンから探す
        text_all = normalize_text(soup.get_text(" "))
        if text_all:
            phone_match = extract_phone_number(text_all)
            if phone_match:
                return phone_match

        return None

    def _extract_postal_code(self, address: Optional[str]) -> Optional[str]:
        """郵便番号を抽出"""
        if address:
            postal = extract_postal_code(address)
            if postal:
                return postal
        return None

    def _extract_field(self, data: dict[str, str], keys: list[str]) -> Optional[str]:
        """
        データから指定されたキーのいずれかの値を取得

        Args:
            data: データ辞書
            keys: 検索するキーのリスト

        Returns:
            Optional[str]: 最初に見つかった値（見つからない場合はNone）
        """
        for key in keys:
            value = data.get(key)
            if value:
                return value
        return None
