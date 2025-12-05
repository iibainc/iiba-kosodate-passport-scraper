"""滋賀県スクレイパー"""

import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import yaml
from tqdm import tqdm
from bs4 import BeautifulSoup

from .....shared.exceptions.errors import HTTPError, ParsingError, ScraperError
from .....shared.http.client import HTTPClient
from .....shared.http.rate_limiter import RateLimiter
from .....shared.logging.config import get_logger
from ...domain.models import Shop
from ...parsers.prefectures.shiga_parser import ShigaParser
from ..base import AbstractPrefectureScraper

logger = get_logger(__name__)


class ShigaScraper(AbstractPrefectureScraper):
    """滋賀県の店舗情報スクレイパー"""

    def __init__(
        self,
        config_path: str = "src/features/scraping/config/prefectures/shiga.yaml",
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

        # 滋賀用パーサーを使用
        self.parser = ShigaParser(prefecture_code, prefecture_name)

        logger.info(f"ShigaScraper initialized: {self.base_url}")

    def scrape(
        self,
        batch_callback=None,
        batch_size: int = 50,
        resume_from_page: Optional[int] = None,
        page_complete_callback=None,
        limit: Optional[int] = None,
    ) -> list[Shop]:
        """
        店舗情報をスクレイピング
        """
        try:
            # 滋賀県はセッション不要のため初期化処理はスキップ

            # 全ページから店舗情報を収集
            all_shops: list[Shop] = []
            current_batch: list[Shop] = []
            seen_urls: set[str] = set()

            pagination = self.config["scraping"]["pagination"]
            start_page = resume_from_page if resume_from_page else pagination["start_page"]
            auto_detect = pagination.get("auto_detect", False)

            if auto_detect:
                end_page = None # ループ内で制御
                max_empty_pages = pagination.get("max_empty_pages", 3)
                empty_page_count = 0
                logger.info(
                    f"Starting scraping with auto-detect: from page {start_page} "
                    f"(batch_size={batch_size}, max_empty_pages={max_empty_pages}, limit={limit})"
                )
            else:
                end_page = pagination["end_page"]
                logger.info(
                    f"Starting scraping: pages {start_page} to {end_page} "
                    f"(batch_size={batch_size}, limit={limit})"
                )

            page_num = start_page
            previous_links_set: Optional[set[str]] = None
            duplicate_page_count = 0
            max_duplicate_pages = 3

            # ページネーションループ
            with tqdm(desc=f"{self.prefecture_name}巡回", initial=start_page - 1) as pbar:
                while True:
                    # 終了条件チェック（固定ページ数の場合）
                    if not auto_detect and end_page and page_num > end_page:
                        break
                    
                    # 件数制限チェック
                    if limit and len(all_shops) >= limit:
                        logger.info(f"Reached limit of {limit} shops. Stopping.")
                        break

                    # 詳細ページのリンクを取得
                    detail_links = self.get_detail_links(page_num)

                    # auto_detectの場合、空ページと重複ページをチェック
                    if auto_detect:
                        if not detail_links:
                            empty_page_count += 1
                            logger.info(
                                f"No links found on page {page_num} "
                                f"(empty count: {empty_page_count}/{max_empty_pages})"
                            )
                            if empty_page_count >= max_empty_pages:
                                logger.info("Reached max consecutive empty pages. Stopping.")
                                break
                        else:
                            empty_page_count = 0

                            # 重複検出
                            current_links_set = set(detail_links)
                            if (
                                previous_links_set is not None
                                and current_links_set == previous_links_set
                            ):
                                duplicate_page_count += 1
                                logger.info(
                                    f"Duplicate page detected ({duplicate_page_count}/{max_duplicate_pages})"
                                )
                                if duplicate_page_count >= max_duplicate_pages:
                                    logger.info(
                                        "Reached max consecutive duplicate pages. Stopping."
                                    )
                                    break
                            else:
                                duplicate_page_count = 0

                            previous_links_set = current_links_set

                    self.rate_limiter.wait()

                    # 各詳細ページをパース
                    for detail_url in tqdm(detail_links, leave=False, desc=f"詳細({page_num})"):
                        if detail_url in seen_urls:
                            continue
                        
                        # 件数制限チェック（詳細ページループ内）
                        if limit and len(all_shops) >= limit:
                            break

                        seen_urls.add(detail_url)

                        shop = self.parse_detail_page(detail_url)

                        if shop:
                            # URLからID生成が難しい場合があるため、detail_urlを使うか、parse_detail_page内で抽出したIDを使う
                            if not shop.shop_id:
                                shop.shop_id = self.generate_shop_id(detail_url)
                                
                            all_shops.append(shop)
                            current_batch.append(shop)

                            if batch_callback and len(current_batch) >= batch_size:
                                try:
                                    batch_callback(current_batch)
                                    current_batch = []
                                except Exception as e:
                                    logger.error(f"Batch callback failed: {e}")

                        self.rate_limiter.wait()
                    
                    # 件数制限でループを抜けた場合、外側のループも抜ける
                    if limit and len(all_shops) >= limit:
                        logger.info(f"Reached limit of {limit} shops. Stopping.")
                        break

                    if page_complete_callback:
                        try:
                            page_complete_callback(page_num)
                        except Exception as e:
                            logger.error(f"Page complete callback failed: {e}")

                    page_num += 1
                    pbar.update(1)

            # 最後のバッチ処理
            if batch_callback and current_batch:
                try:
                    batch_callback(current_batch)
                except Exception as e:
                    logger.error(f"Final batch callback failed: {e}")

            logger.info(f"Scraping completed: {len(all_shops)} shops found")
            return all_shops

        except Exception as e:
            raise ScraperError(f"Failed to scrape {self.prefecture_name}: {e}") from e

    def get_detail_links(self, page_num: int) -> list[str]:
        """一覧ページから詳細ページのリンクを取得"""
        try:
            # 1ページ目と2ページ目以降でURLパターンを分岐
            if page_num == 1:
                # 1ページ目は数字なし: shop/list
                relative_path = "shop/list"
            else:
                # 2ページ目以降: shop/list/{page}
                relative_path = self.config["scraping"]["urls"]["list_page"].format(page=page_num)
            
            # urljoinを使って安全に結合
            # base_url: https://www.hugnavi.net/cheer
            # 結果: https://www.hugnavi.net/cheer/shop/list
            base = self.base_url.rstrip("/") + "/"
            list_url = urljoin(base, relative_path)

            logger.debug(f"Fetching list page: {list_url}")

            # ページを取得
            response = self.http_client.get(list_url, encoding=self.encoding)
            html = response.text

            # 詳細リンクを抽出
            detail_pattern = re.compile(self.config["scraping"]["urls"]["detail_pattern"])

            links: list[str] = []
            seen: set[str] = set()

            soup = BeautifulSoup(html, "html.parser")

            # 【追加】検索範囲をメインエリアに絞る（サイドバーのリンクを拾わないようにする）
            search_area = None
            candidates = ["#main", "#contents", ".main_column", ".contents", "article"]
            for selector in candidates:
                element = soup.select_one(selector)
                if element and len(element.get_text(strip=True)) > 20:
                    search_area = element
                    break
            
            # メインエリアが見つからなければ全体から探す
            if not search_area:
                search_area = soup

            # 詳細リンク収集
            for a_tag in search_area.select("a"):
                href = a_tag.get("href", "")
                if not href:
                    continue

                full_url = urljoin(list_url, href)

                # 同一ドメインチェック
                if (
                    urlparse(full_url).netloc
                    and urlparse(full_url).netloc != urlparse(self.base_url).netloc
                ):
                    continue

                # 詳細ページのパターンチェック
                if detail_pattern.search(full_url):
                    if full_url not in seen:
                        seen.add(full_url)
                        links.append(full_url)

            logger.debug(f"Found {len(links)} detail links on page {page_num} ({list_url})")
            return links

        except HTTPError as e:
            logger.error(f"Failed to get detail links from page {page_num}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error while getting detail links from page {page_num}: {e}")
            return []

    def parse_detail_page(self, url: str) -> Optional[Shop]:
        """詳細ページをパースして店舗情報を取得"""
        try:
            response = self.http_client.get(url, encoding=self.encoding)
            html = response.text

            # ID抽出（URL末尾の数字を利用）
            shop_id = ""
            match = re.search(r"detail/(\d+)", url)
            if match:
                shop_id = match.group(1)

            shop = self.parser.parse(html, url, shop_id)

            if shop:
                logger.debug(f"Parsed shop: {shop.name}")
            else:
                logger.warning(f"Failed to parse shop: {url}")

            return shop

        except HTTPError as e:
            logger.error(f"Failed to fetch detail page {url}: {e}")
            return None
        except ParsingError as e:
            logger.error(f"Failed to parse detail page {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while parsing {url}: {e}")
            return None