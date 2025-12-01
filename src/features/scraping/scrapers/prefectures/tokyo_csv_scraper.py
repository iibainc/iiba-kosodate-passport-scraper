"""東京都CSVスクレイパー"""

import csv
from io import StringIO
from typing import Optional

import yaml
from tqdm import tqdm

from .....shared.exceptions.errors import HTTPError, ParsingError, ScraperError
from .....shared.http.client import HTTPClient
from .....shared.http.rate_limiter import RateLimiter
from .....shared.logging.config import get_logger
from ...domain.models import Shop
from ...parsers.prefectures.tokyo_csv_parser import TokyoCsvParser
from ..base import AbstractPrefectureScraper

logger = get_logger(__name__)


class TokyoCsvScraper(AbstractPrefectureScraper):
    """
    東京都の店舗情報スクレイパー（CSV方式）

    東京都はCSVファイルを直接ダウンロードして解析します。
    """

    def __init__(
        self,
        config_path: str = "src/features/scraping/config/prefectures/tokyo.yaml",
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

        # レート制限を設定（CSV方式では使用頻度は低い）
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

        # CSV設定
        csv_config = self.config["scraping"]["csv"]
        self.csv_url = csv_config["url"]
        self.encoding = csv_config["encoding"]
        self.column_mapping = csv_config["columns"]

        # パーサー初期化
        self.parser = TokyoCsvParser(
            prefecture_code,
            prefecture_name,
            self.column_mapping,
        )

        logger.info(f"TokyoCsvScraper initialized: {self.csv_url}")

    def scrape(
        self,
        batch_callback=None,
        batch_size: int = 50,
        resume_from_page: Optional[int] = None,
        page_complete_callback=None,
    ) -> list[Shop]:
        """
        店舗情報をスクレイピング（CSV方式）

        Args:
            batch_callback: バッチ処理コールバック関数 callback(shops: list[Shop]) -> None
            batch_size: バッチサイズ（店舗数）
            resume_from_page: 使用しない（CSV方式では不要）
            page_complete_callback: 使用しない（CSV方式では不要）

        Returns:
            list[Shop]: 店舗オブジェクトのリスト

        Raises:
            ScraperError: スクレイピング失敗時
        """
        try:
            logger.info(f"Starting CSV scraping: {self.csv_url} (batch_size={batch_size})")

            # CSVダウンロード
            csv_text = self._download_csv()

            # CSV解析
            all_shops = self._parse_csv(csv_text, batch_callback, batch_size)

            logger.info(f"CSV scraping completed: {len(all_shops)} shops found")
            return all_shops

        except Exception as e:
            raise ScraperError(f"Failed to scrape {self.prefecture_name}: {e}") from e

    def _download_csv(self) -> str:
        """
        CSVファイルをダウンロード

        Returns:
            str: CSVテキスト（UTF-8に変換済み）

        Raises:
            HTTPError: ダウンロード失敗時
        """
        try:
            logger.info(f"Downloading CSV: {self.csv_url}")

            response = self.http_client.get(self.csv_url)

            # Shift-JIS → UTF-8に変換（エラー文字は置換）
            csv_text = response.content.decode(self.encoding, errors="replace")

            logger.info(f"CSV downloaded: {len(csv_text)} bytes")
            return csv_text

        except Exception as e:
            raise HTTPError(f"Failed to download CSV: {e}") from e

    def _parse_csv(
        self,
        csv_text: str,
        batch_callback=None,
        batch_size: int = 50,
    ) -> list[Shop]:
        """
        CSVテキストを解析してShopリストに変換

        Args:
            csv_text: CSVテキスト
            batch_callback: バッチ処理コールバック
            batch_size: バッチサイズ

        Returns:
            list[Shop]: 店舗リスト

        Raises:
            ParsingError: 解析失敗時
        """
        try:
            logger.info("Parsing CSV data...")

            all_shops: list[Shop] = []
            current_batch: list[Shop] = []

            # CSVリーダー作成
            csv_reader = csv.reader(StringIO(csv_text))

            # ヘッダー行をスキップ
            next(csv_reader, None)

            # 各行を解析
            for row in tqdm(csv_reader, desc="CSV解析"):
                shop = self.parser.parse_row(row)

                if shop:
                    all_shops.append(shop)
                    current_batch.append(shop)

                    # バッチサイズに達したらコールバックを実行
                    if batch_callback and len(current_batch) >= batch_size:
                        logger.info(f"Processing batch: {len(current_batch)} shops")
                        try:
                            batch_callback(current_batch)
                            current_batch = []  # バッチをクリア
                        except Exception as e:
                            logger.error(f"Batch callback failed: {e}")
                            # エラーが発生してもスクレイピングは続行

            # 最後の残りのバッチを処理
            if batch_callback and current_batch:
                logger.info(f"Processing final batch: {len(current_batch)} shops")
                try:
                    batch_callback(current_batch)
                except Exception as e:
                    logger.error(f"Final batch callback failed: {e}")

            return all_shops

        except Exception as e:
            raise ParsingError(f"Failed to parse CSV: {e}") from e

    def get_detail_links(self, page_num: int) -> list[str]:
        """
        CSV方式では使用しない（抽象メソッドの実装のみ）

        Args:
            page_num: ページ番号（使用しない）

        Returns:
            list[str]: 空のリスト
        """
        return []

    def parse_detail_page(self, url: str) -> Optional[Shop]:
        """
        CSV方式では使用しない（抽象メソッドの実装のみ）

        Args:
            url: 詳細ページURL（使用しない）

        Returns:
            Optional[Shop]: None
        """
        return None
