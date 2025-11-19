#!/usr/bin/env python3
"""ローカル開発用のスクレイピング実行スクリプト"""
import argparse
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.features.batch.orchestrator import BatchOrchestrator
from src.infrastructure.config.settings import Settings
from src.shared.logging.config import setup_logging, get_logger


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="子育て支援パスポートスクレイピングツール（ローカル開発用）"
    )
    parser.add_argument(
        "--prefecture",
        "-p",
        type=str,
        default="08",
        help="都道府県コード（デフォルト: 08 茨城県）",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="デバッグモードで実行",
    )

    args = parser.parse_args()

    # 設定を読み込み
    settings = Settings()

    # ロギングを設定
    log_level = "DEBUG" if args.debug else settings.log_level
    setup_logging(level=log_level)
    logger = get_logger(__name__)

    logger.info("=" * 80)
    logger.info("子育て支援パスポートスクレイピングツール（ローカル開発用）")
    logger.info("=" * 80)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Prefecture Code: {args.prefecture}")
    logger.info(f"Debug Mode: {args.debug}")
    logger.info(f"Firestore Emulator: {settings.firestore_emulator_host or 'Not set (using production)'}")
    logger.info("=" * 80)

    try:
        # オーケストレーターを作成
        orchestrator = BatchOrchestrator(settings)

        # スクレイピングを実行
        logger.info(f"\nStarting scraping for prefecture: {args.prefecture}")
        orchestrator.run_prefecture_scraping(args.prefecture)

        logger.info("\n" + "=" * 80)
        logger.info("Scraping completed successfully!")
        logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.warning("\n\nScraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nScraping failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
