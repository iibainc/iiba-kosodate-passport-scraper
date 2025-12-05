"""和歌山県の店舗情報パーサー"""

import re
from datetime import datetime
from typing import Any, Optional

from bs4 import BeautifulSoup

from .....shared.logging.config import get_logger
from .....shared.utils.text import extract_phone_number, extract_postal_code, normalize_text
from ...domain.models import Shop
from ..base import BaseParser

logger = get_logger(__name__)


class WakayamaParser(BaseParser):
    """
    和歌山県の店舗情報パーサー
    """

    def __init__(self, prefecture_code: str = "30", prefecture_name: str = "和歌山県") -> None:
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
            # div.tbl-r02 tableを対象にする
            table_data = self.extract_table_data(soup, "div.tbl-r02 table")
            data.update(table_data)

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
        # テーブル内の「店舗の名称」から取得
        # extract_table_dataで取得済みかもしれないが、念のため直接探す
        th = soup.find("th", text="店舗の名称")
        if th:
            td = th.find_next_sibling("td")
            if td:
                return normalize_text(td.get_text())

        # 見つからない場合はextract_table_dataの結果に依存するが、
        # ここではNoneを返して呼び出し元で処理させるか、あるいはNoneを返す
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
            business_hours=self._extract_field(data, ["営業時間"]),
            closed_days=self._extract_field(data, ["定休日"]),
            detail_url=url,
            website=self._extract_website(data, soup),
            benefits=self._extract_field(data, ["特典内容"]),
            description=self._extract_field(data, ["店舗のPRポイント"]),
            parking=self._extract_field(data, ["駐車場の有無"]),
            category=self._extract_field(data, ["カテゴリー"]),
            genre=None,  # 和歌山県はジャンルがない場合が多い、あるいはカテゴリーと同じ
            scraped_at=datetime.now(),
            updated_at=datetime.now(),
            is_active=True,
        )

        # 多子世帯向け特典内容があればextra_fieldsに追加
        multi_child_benefit = self._extract_field(data, ["多子世帯向け特典内容"])
        if multi_child_benefit:
            shop.extra_fields["多子世帯向け特典内容"] = multi_child_benefit

        # 対象者があればextra_fieldsに追加
        target = self._extract_field(data, ["対象者"])
        if target:
            shop.extra_fields["対象者"] = target

        # 交通アクセスがあればextra_fieldsに追加
        access = self._extract_field(data, ["交通アクセス"])
        if access:
            shop.extra_fields["交通アクセス"] = access

        return shop

    def _extract_address(self, data: dict[str, str], soup: BeautifulSoup) -> Optional[str]:
        """住所を抽出"""
        # データから探す
        address = self._extract_field(data, ["住所"])
        if address:
            # 郵便番号が含まれている場合があるので除去してもいいが、
            # モデル側で処理するか、ここではそのまま返す
            # 例: 〒640-8154和歌山市十番丁59...
            return address
        return None

    def _extract_phone(self, data: dict[str, str], soup: BeautifulSoup) -> Optional[str]:
        """電話番号を抽出"""
        return self._extract_field(data, ["電話番号"])

    def _extract_postal_code(self, address: Optional[str]) -> Optional[str]:
        """郵便番号を抽出"""
        if address:
            return extract_postal_code(address)
        return None

    def _extract_website(self, data: dict[str, str], soup: BeautifulSoup) -> Optional[str]:
        """WebサイトURLを抽出"""
        # 店舗の名称がリンクになっている場合がある
        th = soup.find("th", text="店舗の名称")
        if th:
            td = th.find_next_sibling("td")
            if td:
                a_tag = td.find("a")
                if a_tag and a_tag.get("href"):
                    return a_tag.get("href")
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
