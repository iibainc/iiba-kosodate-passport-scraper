"""奈良県スクレイパー"""

from typing import Optional

import yaml
from tqdm import tqdm

from .....shared.exceptions.errors import ScraperError
from .....shared.http.client import HTTPClient
from .....shared.http.rate_limiter import RateLimiter
from .....shared.logging.config import get_logger
from ...domain.models import Shop
from ...parsers.prefectures.nara_parser import NaraParser
from ..base import AbstractPrefectureScraper

logger = get_logger(__name__)


class NaraScraper(AbstractPrefectureScraper):
    """
    奈良県の店舗情報スクレイパー
    Nara Super AppのAPI (Apex REST) を直接呼び出してデータを取得する
    """

    def __init__(
        self,
        config_path: str = "src/features/scraping/config/prefectures/nara.yaml",
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
        self.api_url = self.config["scraping"]["api_url"]
        self.parser = NaraParser(prefecture_code, prefecture_name)

        logger.info(f"NaraScraper initialized: {self.base_url}")

    def scrape(
        self,
        batch_callback=None,
        batch_size: int = 50,
        resume_from_page: Optional[int] = None,
        page_complete_callback=None,
    ) -> list[Shop]:
        """
        店舗情報をスクレイピング
        
        APIから全店舗IDリストを取得し、個別に詳細情報を取得する

        Args:
            batch_callback: バッチ処理コールバック関数
            batch_size: バッチサイズ
            resume_from_page: 再開位置（このスクレイパーではページ概念がないため、
                            resume_from_page * batch_size 番目から開始とみなす）
            page_complete_callback: ページ完了コールバック（使用しないが互換性のため維持）

        Returns:
            list[Shop]: 店舗オブジェクトのリスト
        """
        try:
            # 1. 全店舗リストを取得
            logger.info("Fetching shop list from API...")
            list_payload = self.config["scraping"]["list_payload"]
            
            response = self.http_client.post(self.api_url, json=list_payload)
            response_data = response.json()
            
            # エラーチェック
            if "error" in response_data:
                logger.error(f"API Error: {response_data['error']}")
                raise ScraperError(f"API returned error: {response_data['error']}")
                
            shop_list = response_data.get("returnValue", [])
            if not shop_list:
                logger.warning("No shops found in list response")
                return []
                
            total_shops = len(shop_list)
            logger.info(f"Found {total_shops} shops in list")

            all_shops: list[Shop] = []
            current_batch: list[Shop] = []
            
            # 再開位置の計算
            start_index = 0
            if resume_from_page and resume_from_page > 1:
                start_index = (resume_from_page - 1) * batch_size
                logger.info(f"Resuming from index {start_index}")

            # 2. 詳細情報を取得
            for i, item in enumerate(tqdm(shop_list, desc="詳細情報取得")):
                # スキップ処理
                if i < start_index:
                    continue

                shop_id = item.get("id")
                if not shop_id:
                    continue

                try:
                    # 詳細API呼び出し
                    detail_payload = self.config["scraping"]["detail_payload"].copy()
                    # paramsは参照渡しになる可能性があるため、深くコピーするか、ここで再構築
                    # yaml.safe_loadで辞書になっているので、paramsの中身をコピー
                    detail_payload["params"] = detail_payload["params"].copy()
                    detail_payload["params"]["baseId"] = shop_id
                    
                    detail_resp = self.http_client.post(self.api_url, json=detail_payload)
                    detail_data = detail_resp.json()
                    
                    # 詳細データ抽出
                    shop_data = detail_data.get("returnValue")
                    if not shop_data:
                        logger.warning(f"No detail data for {shop_id}")
                        continue
                        
                    # パース
                    shop = self.parser.parse_shop_detail(shop_data)
                    
                    if shop:
                        all_shops.append(shop)
                        current_batch.append(shop)
                        
                        # バッチ処理
                        if len(current_batch) >= batch_size:
                            if batch_callback:
                                batch_callback(current_batch)
                            current_batch = []
                            
                            # 擬似的なページ完了コールバック（バッチごと）
                            if page_complete_callback:
                                current_page = (i // batch_size) + 1
                                page_complete_callback(current_page)

                except Exception as e:
                    logger.error(f"Error processing shop {shop_id}: {e}")
                    # 個別のエラーはログに出して続行
                
                # レート制限
                self.rate_limiter.wait()

            # 最後のバッチ
            if current_batch and batch_callback:
                batch_callback(current_batch)

            logger.info(f"Scraping completed: {len(all_shops)} shops retrieved")
            return all_shops

        except Exception as e:
            raise ScraperError(f"Failed to scrape {self.prefecture_name}: {e}") from e

    # 以下のメソッドは親クラスの抽象メソッド実装のため必要だが、scrape()をオーバーライドしているので使用されない
    def get_detail_links(self, page_num: int) -> list[str]:
        return []

    def parse_detail_page(self, url: str) -> Optional[Shop]:
        return None