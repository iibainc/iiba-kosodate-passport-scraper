# ローカル開発環境セットアップガイド

## 概要

このガイドでは、ローカル開発環境でFirestoreエミュレータを使用してデバッグしながら開発を進める方法を説明します。

## アーキテクチャ（共通化の仕組み）

このプロジェクトでは、都道府県ごとに異なる部分と共通の処理を適切に分離しています：

### 都道府県ごとに実装が必要な部分（3つだけ）

1. **スクレイパー** - `src/features/scraping/scrapers/prefectures/ibaraki.py`
   - `AbstractPrefectureScraper`を継承
   - `scrape()`, `get_detail_links()`, `parse_detail_page()`を実装

2. **パーサー** - `src/features/scraping/parsers/prefectures/ibaraki_parser.py`
   - HTMLから`Shop`オブジェクトを抽出するロジック

3. **設定ファイル** - `src/features/scraping/config/prefectures/ibaraki.yaml`
   - URL、セレクタ、ページネーション設定

### 共通化されている処理（すべての都道府県で共有）

1. **データ変換・登録処理** - `ShopRepository`
   - `save_batch()`: Firestoreへのバッチ保存
   - `Shop.to_firestore_dict()`: データ変換

2. **ジョブ実行** - `PrefectureScrapingJob`
   - スクレイピング → ジオコーディング → Firestore保存 → 通知の全フロー
   - バッチ処理、進捗管理、エラーハンドリング

3. **進捗管理** - `ProgressRepository`
   - ページごとの進捗保存・読み込み・クリア

4. **ジオコーディング** - `GeocodingService`
   - Google Maps APIを使った住所→座標変換

5. **通知** - `SlackNotifier`
   - スクレイピング開始・完了・エラー通知

**新しい都道府県を追加する場合は、スクレイパー・パーサー・設定ファイルの3つだけ実装すれば良い仕組みになっています。**

## 必要な環境

- Python 3.11以上
- Docker Desktop
- Make
- VSCode（推奨）

## セットアップ手順

### 1. 依存関係のインストールとエミュレータ起動

```bash
# 開発環境のセットアップ（依存関係インストール + .envファイル作成）
make dev-setup

# Firestoreエミュレータを起動
make dev-start
```

エミュレータが起動すると以下のURLでアクセスできます：
- **Firestore エミュレータ**: http://localhost:8080
- **Firestore UI（管理画面）**: http://localhost:4000

### 2. アプリケーションの起動

#### 方法A: Makeコマンドで起動（推奨）

```bash
# ホットリロード有効でアプリケーションを起動
make dev-run
```

アプリケーションは http://localhost:8000 で起動します。

#### 方法B: VSCodeデバッガーで起動

1. VSCodeでプロジェクトを開く
2. デバッグパネル（`Cmd+Shift+D`）を開く
3. **"FastAPI Server (Development)"** を選択して実行

ブレークポイントを設定してステップ実行できます。

### 3. スクレイピングの実行

#### 方法A: API経由で実行

```bash
# 茨城県のスクレイピングを実行
make dev-scrape-ibaraki

# または直接curlで
curl -X POST "http://localhost:8000/scrape/08"
```

#### 方法B: スクリプトで直接実行（デバッグ向け）

```bash
# ローカル開発用スクリプト（デバッグモード）
python scripts/run_scraping.py --prefecture 08 --debug
```

#### 方法C: VSCodeデバッガーで実行

1. デバッグパネルで **"Scrape Ibaraki (Debug)"** を選択
2. ブレークポイントを設定して実行

### 4. Firestoreのデータ確認

Firestore UIにアクセスして保存されたデータを確認できます：

http://localhost:4000

以下のコレクションが作成されます：
- `kosodate_passport_shops`: 店舗データ
- `scraping_history`: スクレイピング履歴
- `scraping_progress`: 進捗管理（再開用）

## Makeコマンド一覧

### セットアップ・起動

```bash
make dev-setup           # 開発環境のセットアップ
make dev-start           # Firestoreエミュレータを起動
make dev-run             # アプリケーションを起動（ホットリロード）
make dev-debug           # デバッグモードでアプリケーションを起動
```

### スクレイピング実行

```bash
make dev-scrape-ibaraki  # 茨城県のスクレイピングを実行
```

### ログ・クリーンアップ

```bash
make dev-logs            # Firestoreエミュレータのログを表示
make dev-stop            # Firestoreエミュレータを停止
make dev-clean           # ローカル環境をクリーンアップ
```

## デバッグのヒント

### ブレークポイントを設定する場所

1. **スクレイパー** - `src/features/scraping/scrapers/prefectures/ibaraki.py`
   - `scrape()`: スクレイピングのメインロジック
   - `get_detail_links()`: 一覧ページからリンク取得
   - `parse_detail_page()`: 詳細ページのパース

2. **パーサー** - `src/features/scraping/parsers/prefectures/ibaraki_parser.py`
   - `parse()`: HTMLパース処理

3. **ジョブ** - `src/features/batch/jobs/prefecture_scraping_job.py`
   - `execute()`: ジョブ実行フロー
   - バッチコールバック、ページ完了コールバック

4. **リポジトリ** - `src/features/storage/repositories/shop_repository.py`
   - `save_batch()`: Firestore保存処理

### ログレベルの調整

`.env.development`ファイルでログレベルを変更できます：

```bash
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

### ジオコーディングとSlack通知の無効化

ローカル開発ではAPI呼び出しを避けるため、デフォルトで無効化されています：

```bash
# .env.development
GEOCODING_ENABLED=false
SLACK_ENABLED=false
```

必要に応じて有効化できますが、APIキーが必要です。

### ページ数の制限

テスト時は少ないページ数に設定すると便利です：

`src/features/scraping/config/prefectures/ibaraki.yaml`
```yaml
pagination:
  start_page: 1
  end_page: 3  # テスト用に3ページのみ
  auto_detect: false  # 固定ページ数
```

または`auto_detect: true`にして、連続空ページ数で終了判定：
```yaml
pagination:
  start_page: 1
  auto_detect: true
  max_empty_pages: 2  # 2ページ連続で空なら終了
```

## トラブルシューティング

### Firestoreエミュレータに接続できない

```bash
# エミュレータが起動しているか確認
docker-compose ps

# ログを確認
make dev-logs

# 再起動
make dev-stop
make dev-start
```

### ポート競合エラー

`.env.development`でポート番号を変更：
```bash
PORT=8001  # 8000が使われている場合
```

docker-compose.ymlでFirestoreのポートを変更：
```yaml
ports:
  - "8081:8080"  # 8080が使われている場合
```

### 依存関係のエラー

```bash
# 依存関係を再インストール
make clean
make dev-setup
```

## 新しい都道府県の追加手順

1. **設定ファイルを作成**
   ```bash
   cp src/features/scraping/config/prefectures/ibaraki.yaml \
      src/features/scraping/config/prefectures/tokyo.yaml
   ```
   編集して東京都の情報に変更

2. **パーサーを実装**
   ```bash
   cp src/features/scraping/parsers/prefectures/ibaraki_parser.py \
      src/features/scraping/parsers/prefectures/tokyo_parser.py
   ```
   `parse()`メソッドを東京都のHTML構造に合わせて実装

3. **スクレイパーを実装**
   ```bash
   cp src/features/scraping/scrapers/prefectures/ibaraki.py \
      src/features/scraping/scrapers/prefectures/tokyo.py
   ```
   必要に応じて調整（多くの場合、設定ファイルとパーサーを変更するだけで動作します）

4. **オーケストレーターに追加**
   `src/features/batch/orchestrator.py`の`run_prefecture_scraping()`に都道府県コードを追加

5. **テスト実行**
   ```bash
   python scripts/run_scraping.py --prefecture 13 --debug
   ```

## 本番環境との違い

| 項目 | ローカル開発 | 本番環境 |
|------|-------------|----------|
| Firestore | エミュレータ | Cloud Firestore |
| Secret Manager | 環境変数 | GCP Secret Manager |
| ジオコーディング | 無効 | Google Maps API |
| Slack通知 | 無効 | Webhook通知 |
| ログレベル | DEBUG | INFO |

## 参考リンク

- [Firestore Emulator](https://firebase.google.com/docs/emulator-suite/connect_firestore)
- [VSCode Python Debugging](https://code.visualstudio.com/docs/python/debugging)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
