"""通知機能のドメインモデル"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class NotificationType(str, Enum):
    """通知タイプ"""

    INFO = "info"  # 情報
    SUCCESS = "success"  # 成功
    WARNING = "warning"  # 警告
    ERROR = "error"  # エラー


@dataclass
class NotificationMessage:
    """通知メッセージ"""

    title: str  # メッセージタイトル
    message: str  # メッセージ本文
    notification_type: NotificationType = NotificationType.INFO
    prefecture_code: Optional[str] = None  # 都道府県コード
    prefecture_name: Optional[str] = None  # 都道府県名
    timestamp: datetime = datetime.now()
    metadata: dict[str, Any] = None  # 追加のメタデータ

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}

    @property
    def emoji(self) -> str:
        """通知タイプに応じた絵文字を返す"""
        emoji_map = {
            NotificationType.INFO: "ℹ️",
            NotificationType.SUCCESS: "✅",
            NotificationType.WARNING: "⚠️",
            NotificationType.ERROR: "❌",
        }
        return emoji_map.get(self.notification_type, "📢")

    @property
    def color(self) -> str:
        """Slack用のカラーコードを返す"""
        color_map = {
            NotificationType.INFO: "#36a64f",  # 緑
            NotificationType.SUCCESS: "#2eb886",  # 明るい緑
            NotificationType.WARNING: "#ff9900",  # オレンジ
            NotificationType.ERROR: "#ff0000",  # 赤
        }
        return color_map.get(self.notification_type, "#808080")
