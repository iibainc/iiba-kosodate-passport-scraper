#!/usr/bin/env python3
"""Firestoreのデータを削除するスクリプト"""
import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.infrastructure.config.settings import Settings
from src.features.storage.clients.firestore_client import FirestoreClient
from src.features.storage.repositories.shop_repository import ShopRepository

# 設定を読み込み
settings = Settings()

# Firestoreエミュレータの設定を環境変数に反映
if settings.firestore_emulator_host:
    os.environ["FIRESTORE_EMULATOR_HOST"] = settings.firestore_emulator_host
    print(f"Using Firestore Emulator: {settings.firestore_emulator_host}")
else:
    print("WARNING: This will delete production data!")
    response = input("Are you sure you want to continue? (yes/no): ")
    if response.lower() != "yes":
        print("Cancelled.")
        sys.exit(0)

# Firestoreクライアントを初期化
firestore_client = FirestoreClient(
    project_id=settings.gcp_project_id,
    database_id=settings.firestore_database_id
)

# コレクション名を取得
shops_collection_name = ShopRepository.COLLECTION_NAME
history_collection_name = settings.firestore_history_collection
progress_collection_name = "scraping_progress"

print(f"\nDeleting data from Firestore...")
print(f"  - {shops_collection_name}")
print(f"  - {history_collection_name}")
print(f"  - {progress_collection_name}")

# 各コレクションのドキュメントを削除
collections_to_clear = [
    shops_collection_name,
    history_collection_name,
    progress_collection_name,
]

for collection_name in collections_to_clear:
    try:
        collection = firestore_client.get_collection(collection_name)
        docs = collection.stream()
        
        deleted_count = 0
        for doc in docs:
            doc.reference.delete()
            deleted_count += 1
        
        print(f"  ✓ {collection_name}: {deleted_count} documents deleted")
    except Exception as e:
        print(f"  ✗ {collection_name}: Error - {e}")

print("\n✓ All data cleared successfully!")

