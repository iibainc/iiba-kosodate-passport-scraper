"""CLIエントリーポイント"""
import argparse
import sys

from .features.batch.orchestrator import BatchOrchestrator
from .infrastructure.config.settings import Settings
from .shared.logging.config import get_logger

logger = get_logger(__name__)


def main() -> int:
    """
    メインエントリーポイント

    Returns:
        int: 終了コード（0: 成功, 1: 失敗）
    """
    parser = argparse.ArgumentParser(
        description="子育て支援パスポート加盟店スクレイピングツール"
    )

    parser.add_argument(
        "--prefecture",
        type=str,
        help="スクレイピング対象の都道府県コード（例: 08）",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="設定ファイルで指定された全都道府県をスクレイピング",
    )

    parser.add_argument(
        "--env-file",
        type=str,
        default=".env",
        help="環境変数ファイルのパス（デフォルト: .env）",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="ログレベル",
    )

    args = parser.parse_args()

    try:
        # 設定を読み込み
        settings = Settings(_env_file=args.env_file)

        # ログレベルを上書き
        if args.log_level:
            settings.log_level = args.log_level

        # ロガーを設定
        from .shared.logging.config import setup_logging

        setup_logging(log_level=settings.log_level)

        logger.info("Starting scraping application")
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Project: {settings.project_name}")

        # オーケストレーターを作成
        orchestrator = BatchOrchestrator(settings)

        # スクレイピングを実行
        if args.all:
            logger.info("Running scraping for all target prefectures")
            orchestrator.run_all_target_prefectures()
        elif args.prefecture:
            logger.info(f"Running scraping for prefecture: {args.prefecture}")
            orchestrator.run_prefecture_scraping(args.prefecture)
        else:
            # デフォルト: 設定ファイルの対象都道府県をすべて実行
            logger.info(
                "No specific prefecture specified, running all target prefectures"
            )
            orchestrator.run_all_target_prefectures()

        logger.info("Scraping application completed successfully")
        return 0

    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        return 130  # SIGINT
    except Exception as e:
        logger.error(f"Application failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
