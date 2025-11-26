#!/usr/bin/env python3
"""
愛知県スクレイパーのドライラン検証スクリプト
1. スクレイパーを1ページ分実行
2. Firestoreエミュレータから結果を取得して表示
"""
import os
import sys
from pathlib import Path
from google.cloud import firestore

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.features.batch.orchestrator import BatchOrchestrator
from src.infrastructure.config.settings import Settings
from src.shared.logging.config import setup_logging, get_logger

def main():
    # 設定を読み込み
    settings = Settings()
    
    # Firestoreエミュレータの設定を環境変数に反映
    if settings.firestore_emulator_host:
        os.environ["FIRESTORE_EMULATOR_HOST"] = settings.firestore_emulator_host
        
    setup_logging(level="INFO")
    logger = get_logger(__name__)
    
    logger.info("=== 愛知県スクレイパー ドライラン開始 ===")
    
    # 1. スクレイピング実行（1ページのみ）
    # Configのend_pageを一時的に変更するのは面倒なので、
    # Orchestratorを少しハックするか、Configを読み込んだ後に書き換えるのが良いが、
    # ここではConfigファイルを一時的に書き換えるアプローチをとる
    
    config_path = project_root / "src/features/scraping/config/prefectures/aichi.yaml"
    with open(config_path, "r") as f:
        original_config = f.read()
        
    try:
        # end_pageを19に変更（約100件取得）
        modified_config = original_config.replace("end_page: 1466", "end_page: 19")
        with open(config_path, "w") as f:
            f.write(modified_config)
            
        logger.info("スクレイピングを実行中...")
        orchestrator = BatchOrchestrator(settings)
        orchestrator.run_prefecture_scraping("23")
        
    finally:
        # 設定を元に戻す
        with open(config_path, "w") as f:
            f.write(original_config)
            
    # 2. 結果確認
    logger.info("\n=== 取得結果確認 ===")
    
    # Firestoreクライアント
    db = firestore.Client(project=settings.gcp_project_id, database=settings.firestore_database_id)
    
    logger.info(f"Project: {settings.gcp_project_id}")
    logger.info(f"Emulator: {os.environ.get('FIRESTORE_EMULATOR_HOST')}")
    logger.info(f"Collections: {[c.id for c in db.collections()]}")

    # 最新の店舗を取得（実際のコレクション名を使用）
    shops_ref = db.collection("kosodate_passport_shops")
    
    # 愛知県のデータのみを取得
    all_results = list(shops_ref.stream())
    aichi_results = [r for r in all_results if r.to_dict().get("prefecture_code") == "23"]
    
    if not aichi_results:
        logger.warning("愛知県のデータが見つかりませんでした。")
        return

    print(f"\n愛知県の取得件数: {len(aichi_results)}件")
    print(f"最新10件を表示:\n")
    
    results = aichi_results[:10]
    
    for doc in results:
        data = doc.to_dict()
        print(f"店舗名: {data.get('name')}")
        print(f"住所: {data.get('address')}")
        print(f"電話番号: {data.get('phone')}")
        print(f"URL: {data.get('detail_url')}")
        print("-" * 40)

if __name__ == "__main__":
    main()
