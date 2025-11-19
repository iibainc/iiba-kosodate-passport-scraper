#!/usr/bin/env python3
"""Firestoreのデータを確認するスクリプト"""
from google.cloud import firestore

# Firestoreクライアントを初期化
db = firestore.Client(project="iiba-staging", database="(default)")

# shopsコレクションの件数を確認
shops_ref = db.collection("shops")
shops_count = len(list(shops_ref.limit(1000).stream()))
print(f"shops コレクション: {shops_count}件")

# 最新の店舗データを5件取得
print("\n=== 最新の店舗データ（5件） ===")
for doc in shops_ref.order_by("scraped_at", direction=firestore.Query.DESCENDING).limit(5).stream():
    data = doc.to_dict()
    print(f"  - {doc.id}: {data.get('name')} ({data.get('address', 'N/A')})")

# scraping_historyコレクションの件数を確認
history_ref = db.collection("scraping_history")
history_count = len(list(history_ref.limit(100).stream()))
print(f"\nscraping_history コレクション: {history_count}件")

# 最新の履歴を5件取得
print("\n=== 最新のスクレイピング履歴（5件） ===")
for doc in history_ref.order_by("started_at", direction=firestore.Query.DESCENDING).limit(5).stream():
    data = doc.to_dict()
    print(f"  - {doc.id}: {data.get('prefecture_name')} - {data.get('status')} ({data.get('shops_count', 0)}件)")
