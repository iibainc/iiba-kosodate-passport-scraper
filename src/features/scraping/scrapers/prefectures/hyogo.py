"""兵庫県スクレイパー"""

from typing import Optional

import yaml

from .....shared.exceptions.errors import ScraperError
from .....shared.http.client import HTTPClient
from .....shared.http.rate_limiter import RateLimiter
from .....shared.logging.config import get_logger
from ...domain.models import Shop
from ...parsers.prefectures.hyogo_parser import HyogoParser
from ..base import AbstractPrefectureScraper

logger = get_logger(__name__)


class HyogoScraper(AbstractPrefectureScraper):
    """兵庫県の店舗情報スクレイパー"""

    def __init__(
        self,
        config_path: str = "src/features/scraping/config/prefectures/hyogo.yaml",
        http_client: Optional[HTTPClient] = None,
    ) -> None:
        """
        Args:
            config_path: 設定ファイルのパス
            http_client: HTTPクライアント（Noneの場合は新規作成）
        """
        # 設定ファイルを読み込み
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        prefecture_code = self.config["prefecture"]["code"]
        prefecture_name = self.config["prefecture"]["name"]

        # レート制限を設定
        rate_limit_config = self.config["scraping"]["rate_limit"]
        rate_limiter = RateLimiter(
            min_wait=rate_limit_config["sleep_min"],
            max_wait=rate_limit_config["sleep_max"],
        )

        # 親クラスの初期化
        super().__init__(
            prefecture_code=prefecture_code,
            prefecture_name=prefecture_name,
            http_client=http_client,
            rate_limiter=rate_limiter,
        )

        self.api_url = self.config["scraping"]["api_url"]
        self.base_url = self.config["scraping"]["base_url"]
        self.parser = HyogoParser(prefecture_code, prefecture_name)

        logger.info(f"HyogoScraper initialized: {self.api_url}")

    def scrape(
        self,
        batch_callback=None,
        batch_size: int = 50,
        resume_from_page: Optional[int] = None,
        page_complete_callback=None,
    ) -> list[Shop]:
        """
        店舗情報をスクレイピング
        
        兵庫県はAPIで全データを一度に取得可能

        Args:
            batch_callback: バッチ処理コールバック関数 callback(shops: list[Shop]) -> None
            batch_size: バッチサイズ（店舗数）
            resume_from_page: 未使用（API一括取得のため）
            page_complete_callback: 未使用

        Returns:
            list[Shop]: 店舗オブジェクトのリスト

        Raises:
            ScraperError: スクレイピング失敗時
        """
        try:
            logger.info("Starting Hyogo scraping (API mode)")

            # APIパラメータ
            params = self.config["scraping"]["params"]

            # APIリクエスト
            response = self.http_client.get(self.api_url, params=params)
            data = response.json()

            if not isinstance(data, list):
                raise ScraperError(f"Unexpected API response format: {type(data)}")

            logger.info(f"Fetched {len(data)} items from API")

            all_shops: list[Shop] = []
            current_batch: list[Shop] = []

            for item in data:
                # 詳細URLを生成（SPAなのでIDを使って生成）
                item_id = item.get("item_id")
                detail_url = f"{self.base_url}/HKO_APP/view/shopdetail.html?item_id={item_id}"

                shop = self.parser.parse(item, detail_url)
                
                if shop:
                    all_shops.append(shop)
                    current_batch.append(shop)

                    # バッチ処理
                    if batch_callback and len(current_batch) >= batch_size:
                        try:
                            batch_callback(current_batch)
                            current_batch = []
                        except Exception as e:
                            logger.error(f"Batch callback failed: {e}")

            # 残りのバッチを処理
            if batch_callback and current_batch:
                try:
                    batch_callback(current_batch)
                except Exception as e:
                    logger.error(f"Final batch callback failed: {e}")

            logger.info(f"Scraping completed: {len(all_shops)} shops parsed")
            return all_shops

        except Exception as e:
            raise ScraperError(f"Failed to scrape {self.prefecture_name}: {e}") from e

    def get_detail_links(self, page_num: int) -> list[str]:
        """
        一覧ページから詳細ページのリンクを取得（API使用のため未使用）

        Args:
            page_num: ページ番号

        Returns:
            list[str]: 空リスト
        """
        return []

    def parse_detail_page(self, url: str) -> Optional[Shop]:
        """
        詳細ページをパースして店舗情報を取得（API使用のため未使用）

        Args:
            url: 詳細ページのURL

        Returns:
            Optional[Shop]: None
        """
        return None
