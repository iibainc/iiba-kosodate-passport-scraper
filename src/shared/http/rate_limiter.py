"""レート制限（ポライトクローリング）ユーティリティ"""

import random
import time
from typing import Optional

from ..logging.config import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    レート制限を実装するクラス

    ポライトクローリングのために、リクエスト間にランダムな待機時間を設ける
    """

    def __init__(
        self,
        min_wait: float = 1.0,
        max_wait: float = 2.0,
        requests_per_second: Optional[float] = None,
    ):
        """
        Args:
            min_wait: 最小待機時間（秒）
            max_wait: 最大待機時間（秒）
            requests_per_second: 秒あたりの最大リクエスト数（設定時はmin/max_waitを上書き）
        """
        if requests_per_second:
            # リクエスト/秒から待機時間を計算
            wait_time = 1.0 / requests_per_second
            self.min_wait = wait_time * 0.8  # 若干のバッファ
            self.max_wait = wait_time * 1.2
        else:
            self.min_wait = min_wait
            self.max_wait = max_wait

        self.last_request_time: Optional[float] = None

        logger.debug(
            f"RateLimiter initialized: min_wait={self.min_wait:.2f}s, "
            f"max_wait={self.max_wait:.2f}s"
        )

    def wait(self) -> None:
        """
        適切な待機時間をスリープ

        前回のリクエストからの経過時間を考慮し、
        必要に応じて追加の待機を行う
        """
        current_time = time.time()

        if self.last_request_time is not None:
            elapsed = current_time - self.last_request_time
            wait_time = random.uniform(self.min_wait, self.max_wait)

            if elapsed < wait_time:
                sleep_duration = wait_time - elapsed
                logger.debug(f"Rate limiting: sleeping for {sleep_duration:.2f}s")
                time.sleep(sleep_duration)

        self.last_request_time = time.time()

    def reset(self) -> None:
        """レート制限をリセット"""
        self.last_request_time = None
        logger.debug("RateLimiter reset")


def polite_sleep(min_seconds: float = 1.0, max_seconds: float = 2.0) -> None:
    """
    ポライトクローリング用のランダムスリープ

    Args:
        min_seconds: 最小待機時間（秒）
        max_seconds: 最大待機時間（秒）
    """
    sleep_time = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Polite sleep: {sleep_time:.2f}s")
    time.sleep(sleep_time)
