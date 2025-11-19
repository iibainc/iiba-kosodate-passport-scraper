"""Cloud Run用HTTPサーバー（FastAPI）"""
import asyncio
from typing import Any

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse

from .features.batch.orchestrator import BatchOrchestrator
from .infrastructure.config.settings import Settings
from .shared.logging.config import get_logger, setup_logging

# 設定を読み込み
settings = Settings()

# ロギングを設定
setup_logging(level=settings.log_level)
logger = get_logger(__name__)

# FastAPIアプリケーションを作成
app = FastAPI(
    title="子育て支援パスポートスクレイピングサービス",
    description="全国の子育て支援パスポート加盟店情報をスクレイピングし、Firestoreに保存するバッチサービス",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event() -> None:
    """起動時の処理"""
    logger.info("Application starting up")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Project: {settings.project_name}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """シャットダウン時の処理"""
    logger.info("Application shutting down")


@app.get("/")
async def root() -> dict[str, Any]:
    """ルートエンドポイント"""
    return {
        "service": "子育て支援パスポートスクレイピングサービス",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.environment,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy"}


@app.post("/scrape/{prefecture_code}")
async def scrape_prefecture(
    prefecture_code: str, background_tasks: BackgroundTasks
) -> dict[str, Any]:
    """
    指定された都道府県のスクレイピングを実行

    Args:
        prefecture_code: 都道府県コード（例: 08）
        background_tasks: バックグラウンドタスク

    Returns:
        dict[str, Any]: レスポンス
    """
    try:
        logger.info(f"Received scraping request for prefecture: {prefecture_code}")

        # バックグラウンドタスクとしてスクレイピングを実行
        background_tasks.add_task(run_scraping_task, prefecture_code)

        return {
            "message": f"Scraping started for prefecture {prefecture_code}",
            "prefecture_code": prefecture_code,
            "status": "started",
        }

    except Exception as e:
        logger.error(f"Failed to start scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scrape")
async def scrape_all_prefectures(background_tasks: BackgroundTasks) -> dict[str, Any]:
    """
    設定で指定された全都道府県のスクレイピングを実行

    Args:
        background_tasks: バックグラウンドタスク

    Returns:
        dict[str, Any]: レスポンス
    """
    try:
        logger.info("Received scraping request for all target prefectures")

        # バックグラウンドタスクとしてスクレイピングを実行
        background_tasks.add_task(run_all_scraping_task)

        target_codes = settings.get_target_prefecture_codes()

        return {
            "message": "Scraping started for all target prefectures",
            "target_prefectures": target_codes,
            "status": "started",
        }

    except Exception as e:
        logger.error(f"Failed to start scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """グローバル例外ハンドラー"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error", "detail": str(exc)},
    )


def run_scraping_task(prefecture_code: str) -> None:
    """
    スクレイピングタスクを実行（同期関数）

    Args:
        prefecture_code: 都道府県コード
    """
    try:
        logger.info(f"Starting scraping task for prefecture: {prefecture_code}")

        # オーケストレーターを作成
        orchestrator = BatchOrchestrator(settings)

        # スクレイピングを実行
        orchestrator.run_prefecture_scraping(prefecture_code)

        logger.info(
            f"Scraping task completed for prefecture: {prefecture_code}"
        )

    except Exception as e:
        logger.error(
            f"Scraping task failed for prefecture {prefecture_code}: {e}",
            exc_info=True,
        )


def run_all_scraping_task() -> None:
    """
    全都道府県のスクレイピングタスクを実行（同期関数）
    """
    try:
        logger.info("Starting scraping task for all target prefectures")

        # オーケストレーターを作成
        orchestrator = BatchOrchestrator(settings)

        # スクレイピングを実行
        orchestrator.run_all_target_prefectures()

        logger.info("Scraping task completed for all target prefectures")

    except Exception as e:
        logger.error(
            f"Scraping task failed for all prefectures: {e}", exc_info=True
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
