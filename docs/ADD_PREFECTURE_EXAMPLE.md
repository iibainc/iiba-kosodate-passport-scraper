# 新しい都道府県の追加方法（東京都の例）

新しい都道府県を追加する際の手順とサンプルコードです。

## 📋 Firestoreデータ型について

### ✅ データ型は完全に共通化されています！

**定義場所**: `src/features/scraping/domain/models.py`

- `Shop`クラス（Line 10-145）
- `to_firestore_dict()`メソッド（Line 65-92）- **すべての都道府県で共通**
- `from_firestore_dict()`メソッド（Line 94-122）- **すべての都道府県で共通**

**重要**: 新しい都道府県を追加する際、`Shop`クラスや`to_firestore_dict()`は**変更不要**です。

### Firestoreスキーマ

```json
{
  "shop_id": "13_00001",
  "prefecture_code": "13",
  "prefecture_name": "東京都",
  "name": "店名",
  "address": "住所",
  "phone": "電話番号",
  "business_hours": "営業時間",
  "closed_days": "定休日",
  "detail_url": "https://...",
  "website": "https://...",
  "benefits": "優待内容",
  "description": "紹介コメント",
  "parking": "駐車場情報",
  "latitude": 35.6895,
  "longitude": 139.6917,
  "geocoded_at": "2025-01-15T12:00:00Z",
  "scraped_at": "2025-01-15T12:00:00Z",
  "updated_at": "2025-01-15T12:00:00Z",
  "is_active": true
}
```

すべての都道府県で**同じフォーマット**を使用します。

---

## 🎯 追加手順

### 必要なファイル（3つのみ）

1. **設定ファイル**: `src/features/scraping/config/prefectures/tokyo.yaml` ✅ 作成済み
2. **パーサー**: `src/features/scraping/parsers/prefectures/tokyo_parser.py` ✅ 作成済み
3. **スクレイパー**: `src/features/scraping/scrapers/prefectures/tokyo.py` ✅ 作成済み

---

## ステップ1: オーケストレーターに追加

### `src/features/batch/orchestrator.py`

```python
# ===== ファイルの先頭（import部分）=====
# TODO: 東京都スクレイパーをインポート
from ..scraping.scrapers.prefectures.ibaraki import IbarakiScraper
from ..scraping.scrapers.prefectures.tokyo import TokyoScraper  # 追加


# ===== クラスの中（既存のrun_ibaraki_scrapingの後に追加）=====
class BatchOrchestrator:
    # ... 既存のコード ...

    def run_ibaraki_scraping(self) -> None:
        """茨城県のスクレイピングジョブを実行"""
        # ... 既存のコード ...

    # TODO: 東京都のスクレイピングメソッドを追加
    def run_tokyo_scraping(self) -> None:
        """東京都のスクレイピングジョブを実行"""
        logger.info("Starting Tokyo scraping job")

        # HTTPクライアントを作成
        http_client = HTTPClient(
            timeout=self.settings.scraping_timeout,
            max_retries=self.settings.scraping_retry,
            user_agent=self.settings.scraping_user_agent,
        )

        # スクレイパーを作成
        scraper = TokyoScraper(http_client=http_client)

        # ジョブを実行
        job = PrefectureScrapingJob(
            scraper=scraper,
            geocoding_service=self.geocoding_service,
            shop_repository=self.shop_repository,
            history_repository=self.history_repository,
            progress_repository=self.progress_repository,
            slack_notifier=self.slack_notifier,
        )

        result = job.execute()

        logger.info(f"Tokyo scraping job completed: {result.status.value}")

    def run_prefecture_scraping(self, prefecture_code: str) -> None:
        """指定された都道府県のスクレイピングジョブを実行"""
        logger.info(f"Starting scraping job for prefecture: {prefecture_code}")

        if prefecture_code == "08":
            self.run_ibaraki_scraping()
        # TODO: 東京都を追加
        elif prefecture_code == "13":
            self.run_tokyo_scraping()
        else:
            raise ValueError(
                f"Unsupported prefecture code: {prefecture_code}. "
                f"Currently, only Ibaraki (08) and Tokyo (13) are supported."  # メッセージも更新
            )
```

---

## ステップ2: 都道府県コードの定義を確認

### `src/features/scraping/domain/enums.py`

都道府県コードが定義されているか確認：

```python
class PrefectureCode(Enum):
    """都道府県コード"""

    IBARAKI = ("08", "茨城県", "ibaraki")
    # TODO: 東京都を追加（必要に応じて）
    TOKYO = ("13", "東京都", "tokyo")
```

※ 通常は追加不要ですが、型チェックを厳密にする場合は追加します。

---

## ステップ3: 環境変数の設定

### `.env.development`

```bash
# TODO: 東京都を対象都道府県に追加
TARGET_PREFECTURES=08,13  # 茨城県と東京都
```

### `.env.example`

本番環境用にも同様に追加：

```bash
TARGET_PREFECTURES=08,13
```

---

## ステップ4: テスト実行

### ローカル環境でテスト

```bash
# Firestoreエミュレータを起動
make dev-start

# 東京都のスクレイピングを実行
python scripts/run_scraping.py --prefecture 13 --debug
```

### デバッグ

1. **VSCode**: デバッグパネルで "Scrape Ibaraki (Debug)" の設定を複製
2. **PyCharm**: Run Configuration を複製
3. 引数を `--prefecture 13` に変更

---

## ステップ5: 設定の調整（TODOを埋める）

### `tokyo.yaml`の調整

実際の東京都のサイトを調査して、以下を設定：

```yaml
scraping:
  # TODO: 実際のURLに変更
  base_url: "https://actual-tokyo-kosodate-site.jp"

  # TODO: 文字エンコーディングを確認
  encoding: "utf-8"  # または "shift_jis"

  urls:
    # TODO: 実際のURL構造に合わせる
    list_page: "/list?page={page}"
    detail_pattern: "/detail/\\d+"

  pagination:
    # TODO: 総ページ数を確認、または auto_detect: true に設定
    start_page: 1
    end_page: 50
    auto_detect: false
```

### `tokyo_parser.py`の調整

実際のHTMLを見ながら、セレクタを調整：

```python
def _extract_shop_name(self, soup: BeautifulSoup) -> Optional[str]:
    """店舗名を抽出"""
    # TODO: 実際のHTMLに合わせてセレクタを変更
    name_tag = soup.select_one("h2.actual-class-name")
    if name_tag:
        return normalize_text(name_tag.get_text())
    return None

def _extract_field(self, soup: BeautifulSoup, label: str) -> Optional[str]:
    """ラベルに対応する値を抽出"""
    # TODO: 実際のHTMLフォーマットに合わせて実装
    # パターンA, B, C のいずれかを選択、または独自実装
```

---

## 📝 チェックリスト

新しい都道府県を追加する際のチェックリスト：

### 1. ファイル作成
- [ ] `src/features/scraping/config/prefectures/tokyo.yaml`
- [ ] `src/features/scraping/parsers/prefectures/tokyo_parser.py`
- [ ] `src/features/scraping/scrapers/prefectures/tokyo.py`

### 2. コード修正
- [ ] `src/features/batch/orchestrator.py` - インポート追加
- [ ] `src/features/batch/orchestrator.py` - `run_tokyo_scraping()` 追加
- [ ] `src/features/batch/orchestrator.py` - `run_prefecture_scraping()` に分岐追加

### 3. 設定ファイル調整
- [ ] `tokyo.yaml` - URLとセレクタを実際のサイトに合わせる
- [ ] `.env.development` - `TARGET_PREFECTURES` に追加
- [ ] `.env.example` - `TARGET_PREFECTURES` に追加

### 4. パーサー調整
- [ ] `tokyo_parser.py` - `_extract_shop_name()` のセレクタ調整
- [ ] `tokyo_parser.py` - `_extract_field()` のHTML構造に合わせる

### 5. テスト
- [ ] ローカル環境でスクレイピング実行
- [ ] Firestore UIでデータ確認
- [ ] すべてのフィールドが正しく抽出されているか確認

### 6. デプロイ
- [ ] GitHubにpush
- [ ] Staging環境で動作確認
- [ ] 本番環境へデプロイ（タグを切る）

---

## 🔍 トラブルシューティング

### パースエラーが発生する

1. `tokyo_parser.py`の`_extract_field()`を調整
2. 実際のHTMLを`curl`で取得して確認：
   ```bash
   curl "https://actual-site.jp/detail/123" -o test.html
   ```
3. BeautifulSoupでセレクタをテスト：
   ```python
   from bs4 import BeautifulSoup
   soup = BeautifulSoup(open("test.html"), "html.parser")
   print(soup.select("h2.shop-title"))
   ```

### セッショントークンエラー

1. `tokyo.yaml`の`session.required`を確認
2. 不要な場合は`false`に設定
3. 必要な場合は`tokyo.py`の`_init_session()`を実装

### Firestoreに保存されない

1. `Shop`オブジェクトが正しく作成されているか確認
2. `to_firestore_dict()`は自動的に呼ばれるので変更不要
3. ログを確認：`save_batch()`のログを見る

---

## 💡 ヒント

### 共通化されている部分（変更不要）

- `Shop`クラスの定義
- `to_firestore_dict()`メソッド
- `ShopRepository.save_batch()`
- `PrefectureScrapingJob.execute()`
- スクレイピングのメインループ

### 都道府県ごとに変わる部分（実装が必要）

- URL構造（`tokyo.yaml`）
- HTMLセレクタ（`tokyo_parser.py`）
- セッショントークンの有無（`tokyo.py`の`_init_session()`）

---

## 📚 参考資料

- [茨城県スクレイパー](../src/features/scraping/scrapers/prefectures/ibaraki.py) - 実装の参考
- [茨城県パーサー](../src/features/scraping/parsers/prefectures/ibaraki_parser.py) - 実装の参考
- [ローカル開発ガイド](LOCAL_DEVELOPMENT.md) - デバッグ方法
