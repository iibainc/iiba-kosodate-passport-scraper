"""ロギング設定"""
import logging
import sys
from typing import Optional

# ロガー設定済みフラグ
_logger_configured = False


def setup_logging(
    level: str = "INFO",
    enable_cloud_logging: bool = False,
    project_id: Optional[str] = None,
) -> None:
    """
    ロギングを設定

    Args:
        level: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_cloud_logging: Cloud Loggingを有効にするか
        project_id: GCPプロジェクトID (Cloud Logging有効時に必要)
    """
    global _logger_configured

    if _logger_configured:
        return

    # ログレベルの設定
    log_level = getattr(logging, level.upper(), logging.INFO)

    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 既存のハンドラーをクリア
    root_logger.handlers.clear()

    # フォーマッターの設定
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # コンソールハンドラーの追加
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Cloud Loggingの設定（本番環境用）
    if enable_cloud_logging:
        try:
            from google.cloud import logging as cloud_logging

            client = cloud_logging.Client(project=project_id)
            cloud_handler = cloud_logging.handlers.CloudLoggingHandler(client)
            cloud_handler.setLevel(log_level)
            root_logger.addHandler(cloud_handler)

            logging.info("Cloud Logging enabled")
        except Exception as e:
            logging.warning(f"Failed to enable Cloud Logging: {e}")

    # サードパーティライブラリのログレベルを調整
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)

    _logger_configured = True
    logging.info(f"Logging configured with level: {level}")


def get_logger(name: str) -> logging.Logger:
    """
    指定名のロガーを取得

    Args:
        name: ロガー名（通常は__name__を指定）

    Returns:
        ロガーインスタンス
    """
    return logging.getLogger(name)
