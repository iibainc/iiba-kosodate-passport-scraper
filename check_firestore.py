#!/usr/bin/env python3
"""Firestoreのデータを確認するスクリプト"""
import argparse
import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from google.cloud import firestore
from src.infrastructure.config.settings import Settings
from src.features.scraping.domain.enums import PrefectureCode, PREFECTURE_NAMES
from src.features.storage.repositories.shop_repository import ShopRepository
from src.features.storage.clients.firestore_client import FirestoreClient


def get_prefecture_name(code: str) -> str:
    """都道府県コードから都道府県名を取得"""
    try:
        pref_code = PrefectureCode(code)
        return PREFECTURE_NAMES.get(pref_code, f"不明({code})")
    except ValueError:
        return f"不明({code})"


def get_all_prefecture_stats(firestore_client: FirestoreClient, shops_collection_name: str) -> dict[str, int]:
    """全都道府県の店舗数を取得"""
    stats = {}
    for pref_code in PrefectureCode:
        code = pref_code.value
        count = firestore_client.count_documents(
            shops_collection_name,
            filters=[("prefecture_code", "==", code)]
        )
        if count > 0:
            stats[code] = count
    return stats


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="Firestoreのデータを確認するスクリプト")
    parser.add_argument(
        "--prefecture",
        "-p",
        type=str,
        help="都道府県コード（例: 23, 28）。指定しない場合は全都道府県の統計を表示",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=15,
        help="表示する店舗数の上限（デフォルト: 15）",
    )

    args = parser.parse_args()

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

    # 都道府県コードが指定されている場合
    if args.prefecture:
        prefecture_code = args.prefecture
        prefecture_name = get_prefecture_name(prefecture_code)

        # 指定された都道府県の店舗数をカウント
        prefecture_count = firestore_client.count_documents(
            shops_collection_name,
            filters=[("prefecture_code", "==", prefecture_code)]
        )
        print(f"  {prefecture_name}（{prefecture_code}）: {prefecture_count}件")

        # コレクション参照を取得
        shops_ref = db.collection(shops_collection_name)

        # 最新の店舗データを5件取得
        print("\n=== 最新の店舗データ（5件） ===")
        for doc in shops_ref.order_by("scraped_at", direction=firestore.Query.DESCENDING).limit(5).stream():
            data = doc.to_dict()
            print(f"  - {doc.id}: {data.get('name')} ({data.get('address', 'N/A')}) [都道府県: {data.get('prefecture_code', 'N/A')}]")

        # 指定された都道府県の最新店舗データを取得
        print(f"\n=== {prefecture_name}の最新店舗データ（{args.limit}件） ===")
        prefecture_ref = shops_ref.where("prefecture_code", "==", prefecture_code)
        count = 0
        for doc in prefecture_ref.order_by("scraped_at", direction=firestore.Query.DESCENDING).limit(args.limit).stream():
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

        # 指定された都道府県の履歴を確認
        print(f"\n=== {prefecture_name}のスクレイピング履歴 ===")
        prefecture_history = list(history_ref.where("prefecture_code", "==", prefecture_code).order_by("started_at", direction=firestore.Query.DESCENDING).limit(5).stream())
        if prefecture_history:
            for doc in prefecture_history:
                data = doc.to_dict()
                print(f"  - {doc.id}: {data.get('status')} - {data.get('shops_count', 0)}件 (開始: {data.get('started_at')})")
        else:
            print("  履歴が見つかりませんでした")

    else:
        # 全都道府県の統計を表示
        print("\n=== 都道府県別店舗数 ===")
        stats = get_all_prefecture_stats(firestore_client, shops_collection_name)
        if stats:
            # 都道府県コードでソート
            sorted_stats = sorted(stats.items(), key=lambda x: x[0])
            for code, count in sorted_stats:
                name = get_prefecture_name(code)
                print(f"  {name}（{code}）: {count}件")
        else:
            print("  データが見つかりませんでした")

        # 最新の店舗データを5件取得
        shops_ref = db.collection(shops_collection_name)
        print("\n=== 最新の店舗データ（5件） ===")
        for doc in shops_ref.order_by("scraped_at", direction=firestore.Query.DESCENDING).limit(5).stream():
            data = doc.to_dict()
            pref_code = data.get('prefecture_code', 'N/A')
            pref_name = get_prefecture_name(pref_code) if pref_code != 'N/A' else 'N/A'
            print(f"  - {doc.id}: {data.get('name')} ({data.get('address', 'N/A')}) [{pref_name} ({pref_code})]")

        # scraping_historyコレクションの件数を確認
        history_ref = db.collection(settings.firestore_history_collection)
        history_count = len(list(history_ref.limit(100).stream()))
        print(f"\n{settings.firestore_history_collection} コレクション: {history_count}件")

        # 最新の履歴を5件取得
        print("\n=== 最新のスクレイピング履歴（5件） ===")
        for doc in history_ref.order_by("started_at", direction=firestore.Query.DESCENDING).limit(5).stream():
            data = doc.to_dict()
            print(f"  - {doc.id}: {data.get('prefecture_name')} ({data.get('prefecture_code', 'N/A')}) - {data.get('status')} ({data.get('shops_count', 0)}件)")


if __name__ == "__main__":
    main()
