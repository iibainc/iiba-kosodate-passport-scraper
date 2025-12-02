"""京都府の店舗情報パーサー"""
import re
from datetime import datetime
from typing import Any, Optional

from bs4 import BeautifulSoup

from ...domain.models import Shop
from .....shared.logging.config import get_logger
from .....shared.utils.text import (
    extract_phone_number,
    extract_postal_code,
    normalize_text,
)
from ..base import BaseParser

logger = get_logger(__name__)


class KyotoParser(BaseParser):
    """京都府の店舗情報パーサー"""

    # 除外する汎用タイトル
    GENERIC_TITLES = [
        "きょうと子育て応援パスポート",
        "まもっぷ",
        "協賛店検索",
        "検索結果",
        "店舗詳細",
        "子育て応援パスポートサイト",
        "支援メニュー",
    ]

    def __init__(self, prefecture_code: str = "26", prefecture_name: str = "京都府") -> None:
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

            # 店名を抽出
            shop_name = self._extract_shop_name(soup)
            if not shop_name:
                logger.warning(f"Shop name not found: {url}")
                return None

            # データを抽出
            data: dict[str, Any] = {}

            # 京都のサイトは主に table タグで情報が構成されている
            table_data = self.extract_table_data(soup, "table")
            data.update(table_data)

            # 念のため DL タグも探す
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
        """
        # 1. 記事本文内のタイトルをピンポイントで探す
        # WordPressなどのCMSでよくある「メインコンテンツ内のタイトル」クラス
        priority_selectors = [
            "article h1",           # articleタグ内のh1 (最も確実)
            "main h1",              # mainタグ内のh1
            ".post h1",             # postクラス内のh1
            ".entry-header h1",     # エントリーヘッダー内のh1
            ".entry-title",         # WordPress標準タイトルクラス
            "#content h1",          # コンテンツエリア内のh1
        ]

        for selector in priority_selectors:
            element = soup.select_one(selector)
            if element:
                text = normalize_text(element.get_text())
                if text and all(generic not in text for generic in self.GENERIC_TITLES):
                    return text

        # 2. 上記で見つからない場合、<title>タグから抽出する（これが一番確実な場合が多い）
        if soup.title:
            title_text = normalize_text(soup.title.get_text())
            if title_text:
                # "店舗名 | まもっぷ" のような形式から店名だけを取り出す
                for sep in ["｜", "|", " - ", "："]:
                    if sep in title_text:
                        parts = title_text.split(sep)
                        # 一番左側が店名であることが多い
                        candidate = parts[0].strip()
                        if candidate and all(generic not in candidate for generic in self.GENERIC_TITLES):
                            return candidate
                
                # 区切り文字がない場合でも、除外ワードが含まれていなければ採用
                if all(generic not in title_text for generic in self.GENERIC_TITLES):
                    return title_text

        # 3. 最終手段：ページ内のすべてのH1から、除外ワードを含まない最初のものを探す
        # (H2, H3はサイドバーを拾う確率が高いので見ない)
        for element in soup.select("h1"):
            text = normalize_text(element.get_text())
            if text and all(generic not in text for generic in self.GENERIC_TITLES):
                return text

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
            # 京都のサイトのラベルに合わせて調整
            business_hours=self._extract_field(data, ["営業時間", "開館時間"]),
            closed_days=self._extract_field(data, ["定休日", "休業日", "休館日"]),
            detail_url=url,
            website=self._extract_field(data, ["URL", "ホームページ", "WEBサイト", "公式サイト"]),
            benefits=self._extract_field(
                data,
                [
                    "支援メニュー",
                    "きょうと子育て応援パスポート提示特典",
                ],
            ),
            description=self._extract_field(
                data, ["備考", "PR", "紹介文", "お店からのメッセージ"]
            ),
            parking=self._extract_field(data, ["駐車場情報"]),
            category=self._extract_field(data, ["業種", "ジャンル", "カテゴリ"]),
            genre=self._extract_field(data, ["業種詳細", "サブジャンル"]),
            scraped_at=datetime.now(),
            updated_at=datetime.now(),
            is_active=True,
        )

        # その他のフィールドをextra_fieldsに保存
        excluded_keys = {
            "名称", "店舗名", "施設名",
            "所在地", "住所",
            "電話番号", "TEL",
            "営業時間", "定休日",
            "URL", "ホームページ",
            "特典内容", "サービス内容",
            "備考", "PR",
            "駐車場",
            "業種",
            "アクセス",
        }

        for key, value in data.items():
            if key not in excluded_keys:
                shop.extra_fields[key] = value

        return shop

    def _extract_address(self, data: dict[str, str], soup: BeautifulSoup) -> Optional[str]:
        """住所を抽出"""
        # データから探す (京都は「所在地」が一般的)
        address = self._extract_field(data, ["所在地", "住所", "address"])
        if address:
            return address

        # HTML全体から郵便番号パターンを探して、その周辺を取得するなどのロジックが必要ならここに追加
        # 現状は汎用ロジックのみ
        text_all = normalize_text(soup.get_text(" "))
        if text_all:
            match = re.search(r"(〒?\d{3}-\d{4}[^ \n　]*)", text_all)
            if match:
                return match.group(1)

        return None

    def _extract_phone(self, data: dict[str, str], soup: BeautifulSoup) -> Optional[str]:
        """電話番号を抽出"""
        phone = self._extract_field(data, ["電話番号", "TEL", "Tel", "電話"])
        if phone:
            return phone

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
        """データから指定されたキーのいずれかの値を取得"""
        for key in keys:
            value = data.get(key)
            if value:
                return value
        return None