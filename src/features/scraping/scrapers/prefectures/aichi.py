"""愛知県スクレイパー"""
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import yaml
from tqdm import tqdm

from ...domain.models import Shop
from .....shared.exceptions.errors import HTTPError, ParsingError, ScraperError, SessionError
from .....shared.http.client import HTTPClient
from .....shared.http.rate_limiter import RateLimiter
from .....shared.logging.config import get_logger
from ..base import AbstractPrefectureScraper
from ...parsers.prefectures.aichi_parser import AichiParser

logger = get_logger(__name__)


class AichiScraper(AbstractPrefectureScraper):
    """
    愛知県の店舗情報スクレイパー

    TODO: 以下を確認・調整：
    - セッショントークンの必要性（_init_session()）
    - URL構造（get_detail_links()）
    """

    def __init__(
        self,
        config_path: str = "src/features/scraping/config/prefectures/aichi.yaml",
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
        self.parser = AichiParser(prefecture_code, prefecture_name)

        # セッションとトークン
        self.session_token: Optional[str] = None

        logger.info(f"AichiScraper initialized: {self.base_url}")

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
            # セッショントークンを取得
            self._init_session()

            # TODO: セッションが不要な場合はこのチェックを削除
            if self.config["scraping"]["session"]["required"] and not self.session_token:
                raise SessionError("Failed to initialize session token")

            # 全ページから店舗情報を収集
            all_shops: list[Shop] = []
            current_batch: list[Shop] = []
            seen_urls: set[str] = set()

            pagination = self.config["scraping"]["pagination"]
            start_page = resume_from_page if resume_from_page else pagination["start_page"]
            auto_detect = pagination.get("auto_detect", False)

            # auto_detectの場合はend_pageを無視、そうでない場合は設定値を使用
            if auto_detect:
                end_page = None  # 無限ループ用
                max_empty_pages = pagination.get("max_empty_pages", 3)  # 連続空ページ数
                empty_page_count = 0
                logger.info(
                    f"Starting scraping with auto-detect: from page {start_page} "
                    f"(batch_size={batch_size}, max_empty_pages={max_empty_pages})"
                )
            else:
                end_page = pagination["end_page"]
                if resume_from_page:
                    logger.info(
                        f"Resuming scraping: pages {start_page} to {end_page} (batch_size={batch_size})"
                    )
                else:
                    logger.info(
                        f"Starting scraping: pages {start_page} to {end_page} (batch_size={batch_size})"
                    )

            page_num = start_page
            previous_links_set: Optional[set[str]] = None  # 前ページのリンクセット
            duplicate_page_count = 0  # 重複ページカウント
            max_duplicate_pages = 3  # 連続重複ページ数の上限

            # ページネーションループ
            with tqdm(desc="一覧巡回", initial=start_page - 1) as pbar:
                while True:
                    # 終了条件チェック（固定ページ数の場合）
                    if not auto_detect and page_num > end_page:
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
                                logger.info(
                                    f"Reached {max_empty_pages} consecutive empty pages. "
                                    "Stopping scraping."
                                )
                                break
                        else:
                            # リンクが見つかったらカウントをリセット
                            empty_page_count = 0

                            # 重複ページ検出（前ページと完全に同じリンクセットの場合）
                            current_links_set = set(detail_links)
                            if previous_links_set is not None and current_links_set == previous_links_set:
                                duplicate_page_count += 1
                                logger.info(
                                    f"Page {page_num} has identical links as previous page "
                                    f"(duplicate count: {duplicate_page_count}/{max_duplicate_pages})"
                                )
                                if duplicate_page_count >= max_duplicate_pages:
                                    logger.info(
                                        f"Reached {max_duplicate_pages} consecutive duplicate pages. "
                                        "Last page is repeating. Stopping scraping."
                                    )
                                    break
                            else:
                                duplicate_page_count = 0  # 異なるリンクならリセット

                            previous_links_set = current_links_set

                    # レート制限
                    self.rate_limiter.wait()

                    # 各詳細ページをパース
                    for detail_url in tqdm(
                        detail_links, leave=False, desc=f"詳細({page_num})"
                    ):
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
                    pbar.update(1)

            # 最後の残りのバッチを処理
            if batch_callback and current_batch:
                logger.info(f"Processing final batch: {len(current_batch)} shops")
                try:
                    batch_callback(current_batch)
                except Exception as e:
                    logger.error(f"Final batch callback failed: {e}")

            logger.info(
                f"Scraping completed: {len(all_shops)} shops found"
            )
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
            
            # TODO: URLパラメータの構築方法を調整
            if self.session_token:
                list_url = self.base_url + list_url_template.format(
                    page=page_num, xs=self.session_token
                )
            else:
                list_url = self.base_url + list_url_template.format(page=page_num)

            # ページを取得
            response = self.http_client.get(list_url, encoding=self.encoding)
            html = response.text

            # 詳細リンクを抽出
            detail_pattern = re.compile(
                self.config["scraping"]["urls"]["detail_pattern"]
            )

            links: list[str] = []
            seen: set[str] = set()

            # BeautifulSoupでパース
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            for a_tag in soup.select("a"):
                href = a_tag.get("href", "")
                if not href:
                    continue

                # 絶対URLに変換
                full_url = urljoin(list_url, href)

                # 同一ドメインのみ
                if urlparse(full_url).netloc and urlparse(full_url).netloc != urlparse(
                    self.base_url
                ).netloc:
                    continue

                # 詳細ページのパターンにマッチするか確認
                if detail_pattern.search(full_url):
                    if full_url not in seen:
                        seen.add(full_url)
                        links.append(full_url)

            logger.debug(
                f"Found {len(links)} detail links on page {page_num}"
            )
            return links

        except HTTPError as e:
            logger.error(f"Failed to get detail links from page {page_num}: {e}")
            return []
        except Exception as e:
            logger.error(
                f"Unexpected error while getting detail links from page {page_num}: {e}"
            )
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
        except ParsingError as e:
            logger.error(f"Failed to parse detail page {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while parsing {url}: {e}")
            return None

    def _init_session(self) -> None:
        """
        セッションを初期化し、トークンを取得

        Raises:
            SessionError: セッション初期化に失敗した場合
        """
        # セッションが不要な場合は何もしない
        if not self.config["scraping"]["session"]["required"]:
            return

        try:
            # 検索フォームページにアクセス
            search_form_url = self.base_url + self.config["scraping"]["urls"][
                "search_form"
            ].format(xs="_xiIg.b7z_riD")  # ダミートークン

            logger.info(f"Initializing session: {search_form_url}")

            response = self.http_client.get(
                search_form_url, encoding=self.encoding
            )
            html = response.text

            # フォームをパース
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            form = soup.find("form")

            if not form:
                raise SessionError("Search form not found")

            # フォームアクションとデータを取得
            action = form.get("action")
            if not action:
                raise SessionError("Form action not found")

            # input要素からフォームデータを構築
            form_data = {}
            for input_tag in form.find_all("input"):
                name = input_tag.get("name")
                value = input_tag.get("value", "")
                if name:
                    form_data[name] = value

            # フォームをPOST
            logger.debug(f"Posting form to {action}")
            post_response = self.http_client.post(
                action, data=form_data, encoding=self.encoding
            )

            # レスポンスURLからトークンを抽出
            token_pattern = re.compile(
                self.config["scraping"]["session"]["token_pattern"]
            )
            match = token_pattern.search(post_response.url)

            if match:
                self.session_token = match.group(1)
                logger.info(f"Session token obtained: {self.session_token}")
            else:
                raise SessionError("Failed to extract session token from response URL")

        except HTTPError as e:
            raise SessionError(f"Failed to initialize session: {e}") from e
        except Exception as e:
            raise SessionError(f"Unexpected error during session initialization: {e}") from e
