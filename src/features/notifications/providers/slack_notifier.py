"""Slack通知プロバイダー"""

from typing import Any, Optional

import requests

from ..domain.models import NotificationMessage, NotificationType
from ....shared.exceptions.errors import NotificationError
from ....shared.logging.config import get_logger

logger = get_logger(__name__)


class SlackNotifier:
    """Slack Webhook を使用した通知プロバイダー"""

    def __init__(self, webhook_url: str, default_channel: Optional[str] = None) -> None:
        """
        Args:
            webhook_url: Slack Webhook URL
            default_channel: デフォルトのチャンネル名（オプション）
        """
        self.webhook_url = webhook_url
        self.default_channel = default_channel

        logger.info("SlackNotifier initialized")

    def send(
        self,
        message: NotificationMessage,
        channel: Optional[str] = None,
        username: str = "子育て支援スクレイパー",
    ) -> None:
        """
        通知メッセージをSlackに送信

        Args:
            message: 通知メッセージ
            channel: 送信先チャンネル（Noneの場合はdefault_channelを使用）
            username: 送信者名

        Raises:
            NotificationError: 送信に失敗した場合
        """
        try:
            # Slack Block Kit を使用したリッチメッセージを構築
            payload = self._build_payload(message, channel or self.default_channel, username)

            # Webhookに送信
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )

            response.raise_for_status()

            logger.info(
                f"Slack notification sent: {message.title} ({message.notification_type.value})"
            )

        except requests.RequestException as e:
            raise NotificationError(f"Failed to send Slack notification: {e}") from e
        except Exception as e:
            raise NotificationError(f"Unexpected error during Slack notification: {e}") from e

    def send_simple(
        self,
        text: str,
        channel: Optional[str] = None,
        username: str = "子育て支援スクレイパー",
    ) -> None:
        """
        シンプルなテキストメッセージを送信

        Args:
            text: メッセージテキスト
            channel: 送信先チャンネル
            username: 送信者名

        Raises:
            NotificationError: 送信に失敗した場合
        """
        try:
            payload: dict[str, Any] = {"text": text, "username": username}

            if channel:
                payload["channel"] = channel

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )

            response.raise_for_status()

            logger.info(f"Simple Slack message sent: {text[:50]}...")

        except requests.RequestException as e:
            raise NotificationError(f"Failed to send simple Slack message: {e}") from e
        except Exception as e:
            raise NotificationError(f"Unexpected error during simple Slack message: {e}") from e

    def _build_payload(
        self,
        message: NotificationMessage,
        channel: Optional[str],
        username: str,
    ) -> dict[str, Any]:
        """
        Slack Block Kit ペイロードを構築

        Args:
            message: 通知メッセージ
            channel: 送信先チャンネル
            username: 送信者名

        Returns:
            dict[str, Any]: Slackペイロード
        """
        # ヘッダーセクション
        header_block = {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{message.emoji} {message.title}",
            },
        }

        # メッセージセクション
        message_block = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message.message,
            },
        }

        # フィールド（都道府県情報など）
        fields = []

        if message.prefecture_name:
            fields.append(
                {
                    "type": "mrkdwn",
                    "text": f"*都道府県:*\n{message.prefecture_name}",
                }
            )

        if message.prefecture_code:
            fields.append(
                {
                    "type": "mrkdwn",
                    "text": f"*都道府県コード:*\n{message.prefecture_code}",
                }
            )

        # メタデータフィールド
        if message.metadata:
            for key, value in message.metadata.items():
                # 数値やブール値を適切にフォーマット
                formatted_value = self._format_metadata_value(value)
                fields.append(
                    {
                        "type": "mrkdwn",
                        "text": f"*{key}:*\n{formatted_value}",
                    }
                )

        # フィールドブロック
        blocks = [header_block, message_block]

        if fields:
            fields_block = {
                "type": "section",
                "fields": fields,
            }
            blocks.append(fields_block)

        # コンテキストセクション（タイムスタンプ）
        context_block = {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"<!date^{int(message.timestamp.timestamp())}^{{date_num}} {{time_secs}}|{message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}>",
                }
            ],
        }
        blocks.append(context_block)

        # ペイロードを構築
        payload: dict[str, Any] = {
            "username": username,
            "blocks": blocks,
        }

        if channel:
            payload["channel"] = channel

        # Fallback text
        payload["text"] = f"{message.emoji} {message.title}: {message.message}"

        return payload

    def _format_metadata_value(self, value: Any) -> str:
        """
        メタデータの値をSlack用にフォーマット

        Args:
            value: メタデータの値

        Returns:
            str: フォーマット済み文字列
        """
        if isinstance(value, bool):
            return "✅ はい" if value else "❌ いいえ"
        elif isinstance(value, (int, float)):
            # 数値をカンマ区切りでフォーマット
            return f"{value:,}"
        elif isinstance(value, list):
            # リストを改行区切りでフォーマット
            return "\n".join(f"• {item}" for item in value)
        else:
            return str(value)

    def send_scraping_start(self, prefecture_name: str, prefecture_code: str) -> None:
        """
        スクレイピング開始通知を送信

        Args:
            prefecture_name: 都道府県名
            prefecture_code: 都道府県コード
        """
        message = NotificationMessage(
            title="スクレイピング開始",
            message=f"{prefecture_name}の店舗情報スクレイピングを開始しました。",
            notification_type=NotificationType.INFO,
            prefecture_code=prefecture_code,
            prefecture_name=prefecture_name,
        )

        self.send(message)

    def send_scraping_complete(
        self,
        prefecture_name: str,
        prefecture_code: str,
        total_shops: int,
        new_shops: int,
        updated_shops: int,
        geocoded_shops: int,
        duration_seconds: float,
    ) -> None:
        """
        スクレイピング完了通知を送信

        Args:
            prefecture_name: 都道府県名
            prefecture_code: 都道府県コード
            total_shops: 総店舗数
            new_shops: 新規店舗数
            updated_shops: 更新店舗数
            geocoded_shops: ジオコーディング成功数
            duration_seconds: 処理時間（秒）
        """
        message = NotificationMessage(
            title="スクレイピング完了",
            message=f"{prefecture_name}の店舗情報スクレイピングが完了しました。",
            notification_type=NotificationType.SUCCESS,
            prefecture_code=prefecture_code,
            prefecture_name=prefecture_name,
            metadata={
                "総店舗数": total_shops,
                "新規店舗数": new_shops,
                "更新店舗数": updated_shops,
                "ジオコーディング成功数": geocoded_shops,
                "処理時間": f"{duration_seconds:.1f}秒",
            },
        )

        self.send(message)

    def send_scraping_error(self, prefecture_name: str, prefecture_code: str, error: str) -> None:
        """
        スクレイピングエラー通知を送信

        Args:
            prefecture_name: 都道府県名
            prefecture_code: 都道府県コード
            error: エラーメッセージ
        """
        message = NotificationMessage(
            title="スクレイピングエラー",
            message=f"{prefecture_name}の店舗情報スクレイピング中にエラーが発生しました。\n\n```{error}```",
            notification_type=NotificationType.ERROR,
            prefecture_code=prefecture_code,
            prefecture_name=prefecture_name,
        )

        self.send(message)
