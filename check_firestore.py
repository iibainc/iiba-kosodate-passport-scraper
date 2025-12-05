#!/usr/bin/env python3
"""Firestoreのデータを確認するスクリプト"""
import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from google.cloud import firestore
from src.features.storage.clients.firestore_client import FirestoreClient
from src.features.storage.repositories.shop_repository import ShopRepository
from src.infrastructure.config.settings import Settings


def parse_args():
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(description="Firestore data checker")
    parser.add_argument(
        "-p", "--prefecture", type=str, help="Filter by prefecture code (e.g., 29)"
    )
    parser.add_argument(
        "-l", "--limit", type=int, default=10, help="Limit number of records to show (default: 10)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
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
        database_id=settings.firestore_database_id,
    )
    db = firestore_client.client

    # コレクション名
    shops_collection = ShopRepository.COLLECTION_NAME
    history_collection = settings.firestore_history_collection

    print("\n" + "=" * 60)
    print(f"Firestore Data Check Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 店舗データの統計
    print(f"\n[Collection: {shops_collection}]")
    
    # 全体の件数
    total_count = firestore_client.count_documents(shops_collection)
    print(f"  Total Shops: {total_count}")

    # 都道府県ごとの集計（件数が多い場合は時間がかかる可能性があるため、簡易的な集計にするか検討）
    # ここでは、もしprefecture引数がなければ全件集計、あればその都道府県のみカウント
    if args.prefecture:
        pref_count = firestore_client.count_documents(
            shops_collection, filters=[("prefecture_code", "==", args.prefecture)]
        )
        print(f"  Prefecture {args.prefecture}: {pref_count}")
    else:
        # 都道府県ごとの内訳を表示したいが、count_documentsではgroup byができないため
        # streamで取得して集計するのはコストが高い。
        # 代わりに、最新のドキュメントからいくつかサンプリングして傾向を見るか、
        # ここではシンプルに最新データを表示することに注力する。
        pass

    # 2. 最新の店舗データ表示
    print(f"\n[Latest Shops (Limit: {args.limit})]")
    shops_ref = db.collection(shops_collection)
    
    query = shops_ref.order_by("scraped_at", direction=firestore.Query.DESCENDING)
    
    if args.prefecture:
        # 複合インデックスが必要になる可能性があるため、フィルタ時はscraped_atソートを注意
        # エミュレータなら自動で作られる場合もあるが、まずはシンプルにフィルタのみにするか、
        # クライアントサイドでソートするか。
        # ここでは where -> order_by を試みる
        query = shops_ref.where("prefecture_code", "==", args.prefecture).order_by(
            "scraped_at", direction=firestore.Query.DESCENDING
        )

    try:
        docs = list(query.limit(args.limit).stream())
        if not docs:
            print("  No data found.")
        
        for i, doc in enumerate(docs, 1):
            data = doc.to_dict()
            scraped_at = data.get("scraped_at")
            if isinstance(scraped_at, datetime):
                scraped_at = scraped_at.strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"  {i}. [{data.get('prefecture_code')}] {data.get('name')}")
            print(f"     ID: {doc.id}")
            print(f"     Address: {data.get('address', 'N/A')}")
            print(f"     Updated: {scraped_at}")
            print("     ---")

    except Exception as e:
        print(f"  Error fetching shops: {e}")
        print("  (If using filter + sort, composite index might be missing)")

    # 3. スクレイピング履歴
    print(f"\n[Collection: {history_collection}]")
    history_ref = db.collection(history_collection)
    
    h_query = history_ref.order_by("started_at", direction=firestore.Query.DESCENDING)
    if args.prefecture:
        h_query = history_ref.where("prefecture_code", "==", args.prefecture).order_by(
            "started_at", direction=firestore.Query.DESCENDING
        )

    try:
        h_docs = list(h_query.limit(args.limit).stream())
        if not h_docs:
            print("  No history found.")

        for i, doc in enumerate(h_docs, 1):
            data = doc.to_dict()
            started_at = data.get("started_at")
            if isinstance(started_at, datetime):
                started_at = started_at.strftime("%Y-%m-%d %H:%M:%S")
            
            status = data.get("status", "unknown")
            shops_count = data.get("total_shops", 0)
            new_shops = data.get("new_shops", 0)
            
            print(f"  {i}. {started_at} - {data.get('prefecture_name')} ({data.get('prefecture_code')})")
            print(f"     Status: {status}")
            print(f"     Result: Total={shops_count}, New={new_shops}")
            if data.get("errors"):
                print(f"     Errors: {len(data['errors'])}")
            print("     ---")

    except Exception as e:
        print(f"  Error fetching history: {e}")

    print("\nDone.")