"""和歌山県スクレイパー"""

from typing import Optional
from urllib.parse import urljoin

import yaml

from .....shared.exceptions.errors import HTTPError, ScraperError
from .....shared.http.client import HTTPClient
from .....shared.http.rate_limiter import RateLimiter
from .....shared.logging.config import get_logger
from ...domain.models import Shop
from ...parsers.prefectures.wakayama_parser import WakayamaParser
from ..base import AbstractPrefectureScraper

logger = get_logger(__name__)


class WakayamaScraper(AbstractPrefectureScraper):
    """
    和歌山県の店舗情報スクレイパー
    """

    def __init__(
        self,
        config_path: str = "src/features/scraping/config/prefectures/wakayama.yaml",
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

        self.base_url = self.config["scraping"]["base_url"]
        self.encoding = self.config["scraping"]["encoding"]
        self.parser = WakayamaParser(prefecture_code, prefecture_name)

        logger.info(f"WakayamaScraper initialized: {self.base_url}")

    def scrape(
        self,
        batch_callback=None,
        batch_size: int = 50,
        resume_from_page: Optional[int] = None,
        page_complete_callback=None,
    ) -> list[Shop]:
        """
        店舗情報をスクレイピング

        Args:
            batch_callback: バッチ処理コールバック関数 callback(shops: list[Shop]) -> None
            batch_size: バッチサイズ（店舗数）
            resume_from_page: 再開するページ番号（Noneの場合は最初から）
            page_complete_callback: ページ完了コールバック callback(page_num: int) -> None

        Returns:
            list[Shop]: 店舗オブジェクトのリスト

        Raises:
            ScraperError: スクレイピング失敗時
        """
        try:
            # 全ページから店舗情報を収集
            all_shops: list[Shop] = []
            current_batch: list[Shop] = []
            seen_urls: set[str] = set()

            pagination = self.config["scraping"]["pagination"]
            start_page = resume_from_page if resume_from_page else pagination["start_page"]
            end_page = pagination["end_page"]
            
            # auto_detectの場合はend_pageを無視して無限ループに近い形にするが、
            # 和歌山県はページ数が分かっているのでend_pageを上限にする
            auto_detect = pagination.get("auto_detect", False)
            max_empty_pages = pagination.get("max_empty_pages", 3)
            empty_page_count = 0

            logger.info(f"Starting scraping: pages {start_page} to {end_page} (batch_size={batch_size})")

            page_num = start_page

            # ページネーションループ
            while True:
                # 終了条件チェック
                if page_num > end_page:
                    break

                # 詳細ページのリンクを取得
                detail_links = self.get_detail_links(page_num)

                if not detail_links:
                    empty_page_count += 1
                    logger.info(f"No links found on page {page_num} (empty count: {empty_page_count}/{max_empty_pages})")
                    if auto_detect and empty_page_count >= max_empty_pages:
                        logger.info("Reached max empty pages. Stopping scraping.")
                        break
                else:
                    empty_page_count = 0

                # レート制限
                self.rate_limiter.wait()

                # 各詳細ページをパース
                for detail_url in detail_links:
                    if detail_url in seen_urls:
                        continue

                    seen_urls.add(detail_url)

                    # 店舗情報を取得
                    shop = self.parse_detail_page(detail_url)

                    if shop:
                        # shop_idを設定（URLベースで生成）
                        shop.shop_id = self.generate_shop_id(detail_url)
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

                    # レート制限
                    self.rate_limiter.wait()

                # ページ完了コールバック
                if page_complete_callback:
                    try:
                        page_complete_callback(page_num)
                    except Exception as e:
                        logger.error(f"Page complete callback failed: {e}")

                # 次のページへ
                page_num += 1

            # 最後の残りのバッチを処理
            if batch_callback and current_batch:
                logger.info(f"Processing final batch: {len(current_batch)} shops")
                try:
                    batch_callback(current_batch)
                except Exception as e:
                    logger.error(f"Final batch callback failed: {e}")

            logger.info(f"Scraping completed: {len(all_shops)} shops found")
            return all_shops

        except Exception as e:
            raise ScraperError(f"Failed to scrape {self.prefecture_name}: {e}") from e

    def get_detail_links(self, page_num: int) -> list[str]:
        """
        一覧ページから詳細ページのリンクを取得

        Args:
            page_num: ページ番号

        Returns:
            list[str]: 詳細ページのURLリスト
        """
        try:
            # 一覧ページURLを構築
            list_url_template = self.config["scraping"]["urls"]["list_page"]
            list_url = self.base_url + list_url_template.format(page=page_num)

            # ページを取得
            response = self.http_client.get(list_url, encoding=self.encoding)
            html = response.text

            # BeautifulSoupでパース
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            links: list[str] = []
            
            # テーブル内のリンクを抽出
            # div.tbl-r02 table tbody tr td a
            # あるいは正規表現で抽出
            
            # 正規表現で抽出（シンプルで確実）
            import re
            detail_pattern = re.compile(self.config["scraping"]["urls"]["detail_pattern"])
            
            for a_tag in soup.select("a"):
                href = a_tag.get("href", "")
                if not href:
                    continue
                
                if detail_pattern.search(href):
                    full_url = urljoin(list_url, href)
                    links.append(full_url)

            logger.debug(f"Found {len(links)} detail links on page {page_num}")
            return links

        except HTTPError as e:
            logger.error(f"Failed to get detail links from page {page_num}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error while getting detail links from page {page_num}: {e}")
            return []

    def parse_detail_page(self, url: str) -> Optional[Shop]:
        """
        詳細ページをパースして店舗情報を取得

        Args:
            url: 詳細ページのURL

        Returns:
            Optional[Shop]: 店舗オブジェクト（パース失敗時はNone）
        """
        try:
            # ページを取得
            response = self.http_client.get(url, encoding=self.encoding)
            html = response.text

            # パーサーでパース（shop_idは後で設定）
            shop = self.parser.parse(html, url, "")

            if shop:
                logger.debug(f"Parsed shop: {shop.name}")
            else:
                logger.warning(f"Failed to parse shop: {url}")

            return shop

        except HTTPError as e:
            logger.error(f"Failed to fetch detail page {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while parsing {url}: {e}")
            return None
