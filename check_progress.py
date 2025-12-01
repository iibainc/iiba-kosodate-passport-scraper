#!/usr/bin/env python3
"""スクレイピングの進行状況を確認するスクリプト"""
import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.infrastructure.config.settings import Settings
from src.features.storage.clients.firestore_client import FirestoreClient
from src.features.storage.repositories.shop_repository import ShopRepository
from src.features.storage.repositories.progress_repository import ProgressRepository

# 設定を読み込み
settings = Settings()

# Firestoreエミュレータの設定を環境変数に反映
if settings.firestore_emulator_host:
    os.environ["FIRESTORE_EMULATOR_HOST"] = settings.firestore_emulator_host

# Firestoreクライアントを初期化
firestore_client = FirestoreClient(
    project_id=settings.gcp_project_id,
    database_id=settings.firestore_database_id
)

# リポジトリを初期化
shop_repository = ShopRepository(firestore_client)
progress_repository = ProgressRepository(firestore_client)

# 愛知県の進捗を確認
prefecture_code = "23"
progress = progress_repository.get_progress(prefecture_code)

if progress:
    completed_pages = progress.get("completed_pages", [])
    total_shops = progress.get("total_shops_saved", 0)
    last_shop_id = progress.get("last_shop_id", "N/A")
    
    print(f"愛知県（{prefecture_code}）のスクレイピング進捗:")
    print(f"  完了ページ数: {len(completed_pages)} / 1467ページ (0-1466)")
    print(f"  保存済み店舗数: {total_shops}件")
    print(f"  最後の店舗ID: {last_shop_id}")
    
    if completed_pages:
        print(f"  最新の完了ページ: {max(completed_pages)}")
        print(f"  進捗率: {len(completed_pages) / 1467 * 100:.1f}%")
else:
    print(f"愛知県（{prefecture_code}）の進捗情報が見つかりません（まだ開始されていないか、完了しています）")

# 現在の店舗数を確認
aichi_count = shop_repository.count_by_prefecture(prefecture_code)
print(f"\n現在のFirestoreに保存されている愛知県の店舗数: {aichi_count}件")

