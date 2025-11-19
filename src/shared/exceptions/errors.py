"""カスタム例外定義"""


class ScraperError(Exception):
    """スクレイパー基底例外"""

    pass


class HTTPError(ScraperError):
    """HTTP関連のエラー"""

    pass


class ParsingError(ScraperError):
    """HTML解析エラー"""

    pass


class SessionError(ScraperError):
    """セッション関連のエラー"""

    pass


class GeocodingError(ScraperError):
    """ジオコーディングエラー"""

    pass


class StorageError(ScraperError):
    """ストレージ関連のエラー"""

    pass


class NotificationError(ScraperError):
    """通知関連のエラー"""

    pass


class ConfigurationError(ScraperError):
    """設定エラー"""

    pass


class ValidationError(ScraperError):
    """バリデーションエラー"""

    pass
