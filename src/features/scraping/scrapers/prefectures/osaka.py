"""大阪府スクレイパー"""

from typing import Optional

import yaml
from tqdm import tqdm

from .....shared.exceptions.errors import ScraperError
from .....shared.http.client import HTTPClient
from .....shared.http.rate_limiter import RateLimiter
from .....shared.logging.config import get_logger
from ...domain.models import Shop
from ...parsers.prefectures.osaka_parser import OsakaParser
from ..base import AbstractPrefectureScraper

logger = get_logger(__name__)


class OsakaScraper(AbstractPrefectureScraper):
    """
    大阪府の店舗情報スクレイパー

    APIを使用してデータを取得するため、HTMLパースは不要です。
    """

    def __init__(
        self,
        config_path: str = "src/features/scraping/config/prefectures/osaka.yaml",
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
        self.parser = OsakaParser(prefecture_code, prefecture_name)

        logger.info(f"OsakaScraper initialized: {self.base_url}")

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
            batch_callback: バッチ処理コールバック関数
            batch_size: バッチサイズ（API呼び出し単位ではなく、処理単位）
            resume_from_page: 再開するオフセット（ページ番号ではなく開始インデックスとして扱います）
            page_complete_callback: 完了コールバック

        Returns:
            list[Shop]: 店舗オブジェクトのリスト
        """
        try:
            all_shops: list[Shop] = []
            current_batch: list[Shop] = []
            
            # APIパラメータ設定
            group = self.config["scraping"]["api"]["group"]
            start_index = resume_from_page if resume_from_page else 0
            
            # APIのバッチサイズ（1回のリクエストで取得する件数）
            # 設定ファイルから取得するか、デフォルト値を使用
            api_batch_size = self.config["scraping"]["pagination"].get("batch_size", 10)
            
            total_count = None
            fetched_count = 0
            
            logger.info(f"Starting scraping from index {start_index}")

            with tqdm(desc="データ取得中", initial=start_index) as pbar:
                while True:
                    # APIリクエスト
                    params = {
                        "GROUP": group,
                        "START": start_index
                    }
                    
                    response = self.http_client.get(self.base_url, params=params)
                    data = response.json()
                    
                    # ステータスチェック
                    status = data.get("STATUS")
                    if status not in (200, "200"):
                        logger.error(f"API returned error status: {status}")
                        break
                        
                    # 総件数の更新
                    if total_count is None:
                        total_count = data.get("COUNT", 0)
                        pbar.total = total_count
                        logger.info(f"Total shops to fetch: {total_count}")
                    
                    data_list = data.get("DATALIST", [])
                    if not data_list:
                        logger.info("No more data received")
                        break
                        
                    # データ処理
                    for item in data_list:
                        shop = self.parser.parse(item)
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

                    fetched_count += len(data_list)
                    start_index += len(data_list)
                    pbar.update(len(data_list))
                    
                    # 終了条件
                    if start_index >= total_count:
                        break
                        
                    # レート制限
                    self.rate_limiter.wait()
                    
                    # コールバック（ページ完了の代わりにバッチ完了として扱う）
                    if page_complete_callback:
                        try:
                            page_complete_callback(start_index)
                        except Exception as e:
                            logger.error(f"Page complete callback failed: {e}")

            # 残りのバッチを処理
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
        """
        一覧ページから詳細ページのリンクを取得

        Note: Osaka uses API, so this method is not used.
        """
        return []

    def parse_detail_page(self, url: str) -> Optional[Shop]:
        """
        詳細ページをパースして店舗情報を取得

        Note: Osaka uses API, so this method is not used.
        """
        return None

