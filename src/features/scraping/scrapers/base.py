"""スクレイパーの基底クラス"""
from abc import ABC, abstractmethod
from typing import Any, Optional

from ..domain.models import Shop
from ....shared.http.client import HTTPClient
from ....shared.http.rate_limiter import RateLimiter
from ....shared.logging.config import get_logger

logger = get_logger(__name__)


class AbstractPrefectureScraper(ABC):
    """都道府県スクレイパーの抽象基底クラス"""

    def __init__(
        self,
        prefecture_code: str,
        prefecture_name: str,
        http_client: Optional[HTTPClient] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        """
        Args:
            prefecture_code: 都道府県コード
            prefecture_name: 都道府県名
            http_client: HTTPクライアント（Noneの場合は新規作成）
            rate_limiter: レート制限（Noneの場合は新規作成）
        """
        self.prefecture_code = prefecture_code
        self.prefecture_name = prefecture_name
        self.http_client = http_client or HTTPClient()
        self.rate_limiter = rate_limiter or RateLimiter(
            requests_per_second=1.0, burst_size=1
        )

        logger.info(
            f"Scraper initialized: {self.prefecture_name} ({self.prefecture_code})"
        )

    @abstractmethod
    def scrape(self) -> list[Shop]:
        """
        店舗情報をスクレイピング

        Returns:
            list[Shop]: 店舗オブジェクトのリスト

        Raises:
            ScraperError: スクレイピング失敗時
        """
        pass

    @abstractmethod
    def get_detail_links(self, page_num: int) -> list[str]:
        """
        一覧ページから詳細ページのリンクを取得

        Args:
            page_num: ページ番号

        Returns:
            list[str]: 詳細ページのURLリスト
        """
        pass

    @abstractmethod
    def parse_detail_page(self, url: str) -> Optional[Shop]:
        """
        詳細ページをパースして店舗情報を取得

        Args:
            url: 詳細ページのURL

        Returns:
            Optional[Shop]: 店舗オブジェクト（パース失敗時はNone）
        """
        pass

    def generate_shop_id(self, index: int) -> str:
        """
        店舗IDを生成

        Args:
            index: 連番

        Returns:
            str: 店舗ID（例: "08_00001"）
        """
        return f"{self.prefecture_code}_{index:05d}"

    def close(self) -> None:
        """リソースをクリーンアップ"""
        if self.http_client:
            self.http_client.close()
        logger.info(f"Scraper closed: {self.prefecture_name}")

    def __enter__(self) -> "AbstractPrefectureScraper":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
