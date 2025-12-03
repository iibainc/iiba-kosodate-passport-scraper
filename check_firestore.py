#!/usr/bin/env python3
"""Firestoreのデータを確認するスクリプト"""
import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from google.cloud import firestore
from src.infrastructure.config.settings import Settings
from src.features.storage.repositories.shop_repository import ShopRepository
from src.features.storage.clients.firestore_client import FirestoreClient

# 設定を読み込み
settings = Settings()

# Firestoreエミュレータの設定を環境変数に反映
if settings.firestore_emulator_host:
    os.environ["FIRESTORE_EMULATOR_HOST"] = settings.firestore_emulator_host
    print(f"Using Firestore Emulator: {settings.firestore_emulator_host}")
else:
    print("Using Production Firestore (no emulator configured)")

# Firestoreクライアントを初期化
firestore_client = FirestoreClient(
    project_id=settings.gcp_project_id,
    database_id=settings.firestore_database_id
)
db = firestore_client.client

# 実際のコレクション名を使用（ShopRepositoryで定義されているもの）
shops_collection_name = ShopRepository.COLLECTION_NAME

# shopsコレクションの件数を正確にカウント
shops_count = firestore_client.count_documents(shops_collection_name)
print(f"\n{shops_collection_name} コレクション: {shops_count}件")

# 愛知県の店舗数を正確にカウント
aichi_count = firestore_client.count_documents(
    shops_collection_name,
    filters=[("prefecture_code", "==", "23")]
)
print(f"  愛知県（23）: {aichi_count}件")

# コレクション参照を取得
shops_ref = db.collection(shops_collection_name)

# 最新の店舗データを5件取得
print("\n=== 最新の店舗データ（5件） ===")
for doc in shops_ref.order_by("scraped_at", direction=firestore.Query.DESCENDING).limit(5).stream():
    data = doc.to_dict()
    print(f"  - {doc.id}: {data.get('name')} ({data.get('address', 'N/A')}) [都道府県: {data.get('prefecture_code', 'N/A')}]")

# 愛知県の最新店舗データを15件取得（今回のテスト実行分）
print("\n=== 愛知県の最新店舗データ（15件） ===")
aichi_ref = shops_ref.where("prefecture_code", "==", "23")
count = 0
for doc in aichi_ref.order_by("scraped_at", direction=firestore.Query.DESCENDING).limit(15).stream():
    data = doc.to_dict()
    print(f"  {count+1:2d}. {doc.id}: {data.get('name')} ({data.get('address', 'N/A')}) [更新: {data.get('scraped_at')}]")
    count += 1

# scraping_historyコレクションの件数を確認
history_ref = db.collection(settings.firestore_history_collection)
history_count = len(list(history_ref.limit(100).stream()))
print(f"\n{settings.firestore_history_collection} コレクション: {history_count}件")

# 最新の履歴を5件取得
print("\n=== 最新のスクレイピング履歴（5件） ===")
for doc in history_ref.order_by("started_at", direction=firestore.Query.DESCENDING).limit(5).stream():
    data = doc.to_dict()
    print(f"  - {doc.id}: {data.get('prefecture_name')} ({data.get('prefecture_code', 'N/A')}) - {data.get('status')} ({data.get('shops_count', 0)}件)")

# 愛知県の履歴を確認
print("\n=== 愛知県のスクレイピング履歴 ===")
aichi_history = list(history_ref.where("prefecture_code", "==", "23").order_by("started_at", direction=firestore.Query.DESCENDING).limit(5).stream())
if aichi_history:
    for doc in aichi_history:
        data = doc.to_dict()
        print(f"  - {doc.id}: {data.get('status')} - {data.get('shops_count', 0)}件 (開始: {data.get('started_at')})")
else:
    print("  履歴が見つかりませんでした")
