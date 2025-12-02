"""HTTPクライアント（リトライ機能付き）"""

from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..exceptions.errors import HTTPError
from ..logging.config import get_logger

logger = get_logger(__name__)


class HTTPClient:
    """
    リトライ機能付きHTTPクライアント

    Features:
    - 自動リトライ（指数バックオフ）
    - タイムアウト設定
    - セッション管理
    """

    def __init__(
        self,
        timeout: int = 20,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        status_forcelist: tuple[int, ...] = (500, 502, 503, 504),
        user_agent: Optional[str] = None,
    ):
        """
        Args:
            timeout: リクエストタイムアウト（秒）
            max_retries: 最大リトライ回数
            backoff_factor: バックオフ係数
            status_forcelist: リトライ対象のステータスコード
            user_agent: User-Agentヘッダー
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.status_forcelist = status_forcelist
        self.user_agent = user_agent or ("Mozilla/5.0 (compatible; IIBA-KosodateScraper/1.0)")

        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """セッションを作成"""
        session = requests.Session()

        # リトライ設定
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=self.status_forcelist,
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # デフォルトヘッダー
        session.headers.update({"User-Agent": self.user_agent})

        return session

    def get(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        encoding: Optional[str] = None,
    ) -> requests.Response:
        """
        GETリクエスト

        Args:
            url: リクエストURL
            params: クエリパラメータ
            headers: 追加ヘッダー
            encoding: レスポンスのエンコーディング（Noneの場合は自動検出）

        Returns:
            レスポンスオブジェクト

        Raises:
            HTTPError: リクエスト失敗時
        """
        try:
            logger.debug(f"GET request to {url}")
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )

            # エンコーディング設定
            if encoding:
                response.encoding = encoding

            response.raise_for_status()
            logger.debug(f"GET request successful: {url} (status={response.status_code})")
            return response

        except requests.RequestException as e:
            logger.error(f"GET request failed: {url} - {e}")
            raise HTTPError(f"Failed to GET {url}: {e}") from e

    def post(
        self,
        url: str,
        data: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        encoding: Optional[str] = None,
    ) -> requests.Response:
        """
        POSTリクエスト

        Args:
            url: リクエストURL
            data: フォームデータ
            json: JSONデータ
            headers: 追加ヘッダー
            encoding: レスポンスのエンコーディング

        Returns:
            レスポンスオブジェクト

        Raises:
            HTTPError: リクエスト失敗時
        """
        try:
            logger.debug(f"POST request to {url}")
            response = self.session.post(
                url,
                data=data,
                json=json,
                headers=headers,
                timeout=self.timeout,
            )

            if encoding:
                response.encoding = encoding

            response.raise_for_status()
            logger.debug(f"POST request successful: {url} (status={response.status_code})")
            return response

        except requests.RequestException as e:
            logger.error(f"POST request failed: {url} - {e}")
            raise HTTPError(f"Failed to POST {url}: {e}") from e

    def close(self) -> None:
        """セッションをクローズ"""
        if self.session:
            self.session.close()
            logger.debug("HTTP session closed")

    def __enter__(self) -> "HTTPClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
