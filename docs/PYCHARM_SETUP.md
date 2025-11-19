# PyCharmでのデバッグ環境セットアップ

PyCharmでもVSCodeと同様に、ブレークポイントを使ったステップ実行が可能です。

## クイックスタート

```bash
# 1. Firestoreエミュレータを起動
make dev-start

# 2. PyCharmでプロジェクトを開く
# File → Open → プロジェクトディレクトリを選択

# 3. 右上の実行設定ドロップダウンで "Scrape Ibaraki (Debug)" を選択
# 4. 🐞デバッグアイコンをクリック

# ブレークポイントを設定したい場所で行番号の右側をクリック
# → 赤い●が表示されたらOK
```

デバッグ実行すると、ブレークポイントで停止し、変数の値を確認しながらステップ実行できます。

## 前提条件

- PyCharm Professional または PyCharm Community Edition
- Python 3.11
- Docker Desktop（Firestoreエミュレータ用）

## セットアップ手順

### 1. プロジェクトを開く

```bash
# プロジェクトディレクトリでPyCharmを起動
cd /path/to/iiba-kosodate-passport-scraper
pycharm .
```

または、PyCharmから「Open」でプロジェクトディレクトリを選択します。

### 2. インタープリターの設定

1. **File → Settings** (Windows/Linux) または **PyCharm → Preferences** (macOS)
2. **Project: iiba-kosodate-passport-scraper → Python Interpreter**
3. 右上の⚙️アイコン → **Add Interpreter → Add Local Interpreter...**
4. **Virtualenv Environment** を選択
5. **Existing environment** を選択
6. Interpreter に `.venv/bin/python` を指定
7. **OK** をクリック

### 3. Python環境プラグインのインストール（推奨）

1. **File → Settings → Plugins**
2. 以下のプラグインをインストール：
   - **Python** (Community版ではデフォルト)
   - **EnvFile** (環境変数ファイルのサポート)
   - **Docker** (Dockerサポート)

### 4. Run/Debug Configurationsの確認

プロジェクトを開くと、以下の実行設定が自動的に読み込まれます：

- **FastAPI Server (Development)** - FastAPIサーバーをデバッグモードで起動
- **Scrape Ibaraki (Debug)** - 茨城県のスクレイピングをデバッグ実行
- **Python** - デフォルトのPython実行設定（.env.development自動読み込み）

右上の実行設定ドロップダウンで確認できます。

#### 手動で設定を確認・編集する場合

1. 右上の実行設定ドロップダウン → **Edit Configurations...**
2. 左側のリストから設定を選択
3. 以下の項目を確認：
   - **Environment variables**: `.env.development` が設定されているか
   - **Working directory**: `$PROJECT_DIR$` が設定されているか
   - **Python interpreter**: `.venv/bin/python` が設定されているか

## 使い方

### 1. Firestoreエミュレータの起動

ターミナルで以下を実行：

```bash
make dev-start
```

または、PyCharmのターミナル（下部パネル）で実行できます。

### 2. FastAPIサーバーのデバッグ実行

#### 方法A: 実行設定から起動

1. 右上の実行設定ドロップダウンで **"FastAPI Server (Development)"** を選択
2. 🐞デバッグアイコン（虫のアイコン）をクリック

#### 方法B: ショートカットキー

- **デバッグ実行**: `Ctrl+D` (Windows/Linux) / `Control+D` (macOS)
- **通常実行**: `Shift+F10` (Windows/Linux) / `Control+R` (macOS)

サーバーが起動したら http://localhost:8000 でアクセスできます。

### 3. スクレイピングのデバッグ実行

#### 方法A: 実行設定から起動

1. 右上の実行設定ドロップダウンで **"Scrape Ibaraki (Debug)"** を選択
2. 🐞デバッグアイコンをクリック

#### 方法B: ファイルから直接実行

1. `scripts/run_scraping.py` を開く
2. エディタ内で右クリック → **Debug 'run_scraping'**
3. または、エディタ右上の緑の▶️アイコン → **Debug**

### 4. ブレークポイントの設定

#### ブレークポイントを設定する

1. コードエディタで行番号の右側（左端の余白）をクリック
2. 赤い●が表示されたらブレークポイント設定完了

#### おすすめのブレークポイント設定箇所

**スクレイパー** - `src/features/scraping/scrapers/prefectures/ibaraki.py`
- 127行目: `while True:` - ページネーションループの開始
- 133行目: `detail_links = self.get_detail_links(page_num)` - リンク取得
- 167行目: `shop = self.parse_detail_page(detail_url)` - 店舗情報のパース

**パーサー** - `src/features/scraping/parsers/prefectures/ibaraki_parser.py`
- `parse()` メソッドの先頭 - HTMLパース処理

**ジョブ** - `src/features/batch/jobs/prefecture_scraping_job.py`
- 122行目: `def process_batch(batch_shops: list) -> None:` - バッチ処理
- 164行目: `shops = self.scraper.scrape(...)` - スクレイピング実行

**リポジトリ** - `src/features/storage/repositories/shop_repository.py`
- 67行目: `def save_batch(self, shops: list[Shop]) -> dict[str, int]:` - Firestore保存

### 5. デバッグ機能の使い方

デバッグ実行中に以下の操作ができます：

| 操作 | ショートカット (Windows/Linux) | ショートカット (macOS) |
|------|-------------------------------|----------------------|
| ステップオーバー（次の行へ） | `F8` | `F8` |
| ステップイン（関数内へ） | `F7` | `F7` |
| ステップアウト（関数から出る） | `Shift+F8` | `Shift+F8` |
| 次のブレークポイントまで実行 | `F9` | `F9` / `Cmd+Option+R` |
| 実行を再開 | `F9` | `F9` |
| デバッグを停止 | `Ctrl+F2` | `Cmd+F2` |

#### 変数の確認

- **Variables パネル**: 現在のスコープ内の全変数を表示
- **Watches パネル**: 監視したい式を追加（右クリック → Add to Watches）
- **Console パネル**: 対話的にPythonコードを実行

#### 条件付きブレークポイント

1. ブレークポイント（赤い●）を右クリック
2. **More** または **Edit Breakpoint** をクリック
3. **Condition** に条件式を入力（例: `page_num == 5`）
4. **Done** をクリック

特定の条件でのみ停止させたい場合に便利です。

### 6. ログの確認

#### Firestoreエミュレータのログ

```bash
# ターミナルで
make dev-logs
```

#### アプリケーションのログ

デバッグコンソール（下部パネル）に表示されます。

### 7. Firestoreデータの確認

http://localhost:4000 でFirestore UIにアクセスして、保存されたデータを確認できます。

## デバッグのヒント

### 1. パフォーマンスプロファイリング

1. **Run → Profile 'Scrape Ibaraki (Debug)'**
2. 実行後にプロファイリング結果が表示される
3. どの関数が時間を消費しているか確認できる

### 2. メモリ使用量の確認

1. **View → Tool Windows → Profiler**
2. メモリプロファイラーを有効化
3. メモリリークを検出できる

### 3. リモートデバッグ

Cloud Run上で動作中のアプリケーションをデバッグすることも可能です（高度な使い方）。

### 4. テストのデバッグ

1. `tests/` ディレクトリでテストファイルを開く
2. テスト関数の横に表示される緑の▶️アイコンをクリック
3. **Debug** を選択

## トラブルシューティング

### インタープリターが見つからない

1. ターミナルで仮想環境を作成：
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-dev.txt
   ```
2. PyCharmを再起動
3. インタープリター設定を再度確認

### EnvFileプラグインが動作しない

1. **Settings → Plugins** で EnvFile が有効化されているか確認
2. Run Configuration で **EnvFile** タブが表示されるか確認
3. `.env.development` を手動で追加

### ブレークポイントで停止しない

1. デバッグモード（🐞アイコン）で実行しているか確認
2. ブレークポイントが有効化されているか確認（灰色ではなく赤色）
3. コードが実際に実行されるパスにあるか確認

### Firestoreエミュレータに接続できない

```bash
# エミュレータが起動しているか確認
docker-compose ps

# 環境変数が設定されているか確認
echo $FIRESTORE_EMULATOR_HOST
# 出力: localhost:8080

# .env.development を確認
cat .env.development | grep FIRESTORE_EMULATOR_HOST
```

## VSCodeとの違い

| 機能 | VSCode | PyCharm |
|------|--------|---------|
| ブレークポイント | ✅ | ✅ |
| ステップ実行 | ✅ | ✅ |
| 変数の監視 | ✅ | ✅ |
| 条件付きブレークポイント | ✅ | ✅ |
| プロファイリング | 拡張機能が必要 | ✅ 標準機能 |
| リファクタリング | 基本機能のみ | ✅ 高度な機能 |
| コード補完 | 良い | より高度 |
| 型チェック統合 | 拡張機能が必要 | ✅ 標準機能 |

PyCharmは特に大規模プロジェクトのリファクタリングや型チェックに強みがあります。

## 参考リンク

- [PyCharm公式: Python デバッグ](https://www.jetbrains.com/help/pycharm/debugging-your-first-python-application.html)
- [PyCharm公式: Run/Debug Configurations](https://www.jetbrains.com/help/pycharm/run-debug-configuration.html)
- [EnvFile Plugin](https://plugins.jetbrains.com/plugin/7861-envfile)
