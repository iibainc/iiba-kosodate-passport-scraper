"""東京都パーサー"""

from typing import Optional

from bs4 import BeautifulSoup

from ...domain.models import Shop
from ....shared.exceptions.errors import ParsingError
from ....shared.logging.config import get_logger
from ....shared.utils.text import (
    normalize_text,
    extract_phone_number,
    extract_postal_code,
)

logger = get_logger(__name__)


class TokyoParser:
    """
    東京都の店舗情報パーサー

    HTMLから店舗情報（Shopオブジェクト）を抽出します。
    """

    def __init__(self, prefecture_code: str, prefecture_name: str) -> None:
        """
        Args:
            prefecture_code: 都道府県コード（"13"）
            prefecture_name: 都道府県名（"東京都"）
        """
        self.prefecture_code = prefecture_code
        self.prefecture_name = prefecture_name

    def parse(self, html: str, url: str, shop_id: str) -> Optional[Shop]:
        """
        HTMLから店舗情報を抽出

        Args:
            html: HTMLコンテンツ
            url: 詳細ページのURL
            shop_id: 店舗ID

        Returns:
            Optional[Shop]: 店舗オブジェクト（パース失敗時はNone）

        Raises:
            ParsingError: パース失敗時
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # ===================================
            # TODO: 以下のセクションを東京都のHTML構造に合わせて修正
            # ===================================

            # 1. 店舗名の取得
            # TODO: 東京都のHTMLから店舗名を抽出するセレクタを確認
            name = self._extract_shop_name(soup)
            if not name:
                logger.warning(f"Shop name not found: {url}")
                return None

            # 2. 基本情報の取得
            # TODO: 以下の情報を東京都のHTMLから抽出
            address = self._extract_field(soup, "住所")
            phone = self._extract_field(soup, "電話")
            business_hours = self._extract_field(soup, "営業時間")
            closed_days = self._extract_field(soup, "定休日")
            parking = self._extract_field(soup, "駐車場")
            website = self._extract_field(soup, "ホームページ")
            benefits = self._extract_field(soup, "優待内容")
            description = self._extract_field(soup, "紹介")

            # 3. 郵便番号の抽出（住所から自動抽出）
            postal_code = None
            if address:
                postal_code = extract_postal_code(address)

            # 4. 電話番号の正規化
            if phone:
                phone = extract_phone_number(phone)

            # 5. Shopオブジェクトの作成（共通フォーマット）
            shop = Shop(
                shop_id=shop_id,
                prefecture_code=self.prefecture_code,
                prefecture_name=self.prefecture_name,
                name=name,
                address=address,
                phone=phone,
                business_hours=business_hours,
                closed_days=closed_days,
                detail_url=url,
                website=website,
                benefits=benefits,
                description=description,
                parking=parking,
                postal_code=postal_code,
            )

            # 検索用キーワードを生成
            shop.generate_search_terms()

            return shop

        except Exception as e:
            raise ParsingError(f"Failed to parse shop detail: {e}") from e

    def _extract_shop_name(self, soup: BeautifulSoup) -> Optional[str]:
        """
        店舗名を抽出

        TODO: 東京都のHTMLから店舗名を抽出するロジックを実装
        """
        # パターン1: h2.shop-titleから取得
        name_tag = soup.select_one("h2.shop-title")
        if name_tag:
            return normalize_text(name_tag.get_text())

        # パターン2: h1から取得
        name_tag = soup.find("h1")
        if name_tag:
            return normalize_text(name_tag.get_text())

        # パターン3: .titleクラスから取得
        name_tag = soup.select_one(".title")
        if name_tag:
            return normalize_text(name_tag.get_text())

        return None

    def _extract_field(self, soup: BeautifulSoup, label: str) -> Optional[str]:
        """
        ラベルに対応する値を抽出

        TODO: 東京都のHTMLフォーマットに合わせて実装
        以下は一般的なパターンのサンプル実装です。
        """
        # パターンA: <table>形式
        # <tr><th>住所</th><td>東京都...</td></tr>
        for tr in soup.select("table tr"):
            th = tr.find("th")
            td = tr.find("td")
            if th and td and label in th.get_text():
                return normalize_text(td.get_text())

        # パターンB: <dl>形式
        # <dt>住所</dt><dd>東京都...</dd>
        for dt in soup.find_all("dt"):
            if label in dt.get_text():
                dd = dt.find_next_sibling("dd")
                if dd:
                    return normalize_text(dd.get_text())

        # パターンC: <div class="field">形式
        # <div class="field">
        #   <span class="label">住所</span>
        #   <span class="value">東京都...</span>
        # </div>
        for field in soup.select(".field, .info-row"):
            label_tag = field.select_one(".label, .field-label")
            value_tag = field.select_one(".value, .field-value")
            if label_tag and value_tag and label in label_tag.get_text():
                return normalize_text(value_tag.get_text())

        return None

    def _extract_from_table(self, soup: BeautifulSoup) -> dict[str, str]:
        """
        テーブル形式の情報を一括抽出

        TODO: 必要に応じて使用
        """
        data = {}
        for tr in soup.select("table.shop-info tr"):
            th = tr.find("th")
            td = tr.find("td")
            if th and td:
                key = normalize_text(th.get_text())
                value = normalize_text(td.get_text())
                data[key] = value
        return data

    def _extract_from_dl(self, soup: BeautifulSoup) -> dict[str, str]:
        """
        定義リスト形式の情報を一括抽出

        TODO: 必要に応じて使用
        """
        data = {}
        for dt in soup.select("dl.shop-details dt"):
            dd = dt.find_next_sibling("dd")
            if dd:
                key = normalize_text(dt.get_text())
                value = normalize_text(dd.get_text())
                data[key] = value
        return data
