"""パーサーの基底クラス"""

from abc import ABC, abstractmethod
from typing import Optional

from bs4 import BeautifulSoup

from ....shared.logging.config import get_logger
from ....shared.utils.text import normalize_text
from ..domain.models import Shop

logger = get_logger(__name__)


class BaseParser(ABC):
    """HTMLパーサーの抽象基底クラス"""

    def __init__(self) -> None:
        """パーサーを初期化"""
        logger.debug(f"{self.__class__.__name__} initialized")

    @abstractmethod
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
        pass

    def create_soup(self, html: str) -> BeautifulSoup:
        """
        BeautifulSoupオブジェクトを作成

        Args:
            html: HTML文字列

        Returns:
            BeautifulSoup: パース済みオブジェクト
        """
        return BeautifulSoup(html, "html.parser")

    def extract_text(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        """
        セレクターで要素を取得し、テキストを正規化して返す

        Args:
            soup: BeautifulSoupオブジェクト
            selector: CSSセレクター

        Returns:
            Optional[str]: 正規化されたテキスト（見つからない場合はNone）
        """
        element = soup.select_one(selector)
        if element:
            return normalize_text(element.get_text())
        return None

    def extract_text_multi(self, soup: BeautifulSoup, selectors: list[str]) -> Optional[str]:
        """
        複数のセレクターから最初に見つかったテキストを返す

        Args:
            soup: BeautifulSoupオブジェクト
            selectors: CSSセレクターのリスト

        Returns:
            Optional[str]: 正規化されたテキスト（見つからない場合はNone）
        """
        for selector in selectors:
            text = self.extract_text(soup, selector)
            if text:
                return text
        return None

    def extract_table_data(
        self, soup: BeautifulSoup, table_selector: str = "table"
    ) -> dict[str, str]:
        """
        テーブルからキー・バリューペアを抽出

        Args:
            soup: BeautifulSoupオブジェクト
            table_selector: テーブルのCSSセレクター

        Returns:
            dict[str, str]: キー・バリューのマッピング
        """
        data = {}

        for table in soup.select(table_selector):
            rows = table.select("tr")
            for row in rows:
                th = row.find("th")
                td = row.find("td")

                if th and td:
                    key = normalize_text(th.get_text())
                    value = normalize_text(td.get_text())

                    if key and value:
                        data[key] = value

        return data

    def extract_dl_data(self, soup: BeautifulSoup, dl_selector: str = "dl") -> dict[str, str]:
        """
        定義リスト（dl/dt/dd）からキー・バリューペアを抽出

        Args:
            soup: BeautifulSoupオブジェクト
            dl_selector: dlのCSSセレクター

        Returns:
            dict[str, str]: キー・バリューのマッピング
        """
        data = {}

        for dl in soup.select(dl_selector):
            dts = dl.find_all("dt")
            dds = dl.find_all("dd")

            if len(dts) == len(dds) and len(dts) > 0:
                for dt, dd in zip(dts, dds):
                    key = normalize_text(dt.get_text())
                    value = normalize_text(dd.get_text())

                    if key and value:
                        data[key] = value

        return data
