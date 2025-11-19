# Add Prefecture Skill

新しい都道府県のスクレイパーを追加するスキルです。

## 実行方法

```
@add-prefecture
```

または

```
新しい都道府県を追加して
```

## タスク

新しい都道府県のスクレイパーを追加するために、以下のタスクを実行します：

### 1. 都道府県情報の確認

まず、以下の情報を確認してください：

- 都道府県名（例: 東京都）
- 都道府県コード（例: 13）
- 英語名（例: tokyo）

**ユーザーに質問：**
- "追加する都道府県名を教えてください（例: 東京都）"
- "都道府県コードを教えてください（例: 13）"
- "英語名を教えてください（例: tokyo）"

### 2. 設定ファイルの作成

`src/features/scraping/config/prefectures/{english_name}.yaml`を作成します。

以下のテンプレートを使用してください：

```yaml
prefecture:
  code: "{code}"  # 都道府県コード
  name: "{name}"  # 都道府県名
  name_en: "{english_name}"  # 英語名

scraping:
  # TODO: {name}の子育て支援パスポートサイトのベースURLを調査して設定
  base_url: "https://www.example-{english_name}-kosodate.jp"

  # TODO: 文字エンコーディングを確認（多くはutf-8だが、shift_jisの場合もある）
  encoding: "utf-8"  # または "shift_jis"

  urls:
    # TODO: 各ページのURL構造を調査して設定
    search_form: "/search?category=kosodate"
    list_page: "/list?page={{page}}"
    detail_pattern: "/detail/\\d+"

  pagination:
    start_page: 1
    # TODO: 以下のいずれかを選択
    # 【方法A】固定ページ数（事前に総ページ数がわかる場合）
    end_page: 100
    auto_detect: false
    # 【方法B】自動検出（ページ数が不明な場合）
    # auto_detect: true
    # max_empty_pages: 3

  session:
    # TODO: セッショントークンが必要か確認（不要な場合はfalse）
    required: false
    token_pattern: "session_id=([A-Za-z0-9_-]+)"

  selectors:
    # TODO: HTMLの構造を調査して、適切なCSSセレクタを設定
    shop_name:
      - "h2.shop-title"
      - "h1"
      - ".title"
    table: "table.shop-info tr"
    dl: "dl.shop-details"

  rate_limit:
    # TODO: サイトへの負荷を考慮してレート制限を設定
    sleep_min: 1.0
    sleep_max: 2.0
```

### 3. パーサーの作成

`src/features/scraping/parsers/prefectures/{english_name}_parser.py`を作成します。

茨城県パーサー（`ibaraki_parser.py`）をベースに、以下のコメントを含めてください：

```python
"""
TODO: {name}のHTMLから店舗情報を抽出するロジックを実装

以下のメソッドを{name}のHTML構造に合わせて修正：
- _extract_shop_name(): 店舗名の抽出
- _extract_field(): 各フィールドの抽出

参考: src/features/scraping/parsers/prefectures/ibaraki_parser.py
"""
```

### 4. スクレイパーの作成

`src/features/scraping/scrapers/prefectures/{english_name}.py`を作成します。

茨城県スクレイパー（`ibaraki.py`）をベースに、クラス名を変更してください：

```python
class {ClassName}Scraper(AbstractPrefectureScraper):
    """
    {name}の店舗情報スクレイパー

    TODO: 以下を確認・調整：
    - セッショントークンの必要性（_init_session()）
    - URL構造（get_detail_links()）
    """
```

### 5. オーケストレーターの更新

`src/features/batch/orchestrator.py`に以下を追加：

1. **インポート追加**
```python
from ..scraping.scrapers.prefectures.{english_name} import {ClassName}Scraper
```

2. **スクレイピングメソッド追加**
```python
def run_{english_name}_scraping(self) -> None:
    """
    {name}のスクレイピングジョブを実行
    """
    logger.info("Starting {name} scraping job")

    http_client = HTTPClient(
        timeout=self.settings.scraping_timeout,
        max_retries=self.settings.scraping_retry,
        user_agent=self.settings.scraping_user_agent,
    )

    scraper = {ClassName}Scraper(http_client=http_client)

    job = PrefectureScrapingJob(
        scraper=scraper,
        geocoding_service=self.geocoding_service,
        shop_repository=self.shop_repository,
        history_repository=self.history_repository,
        progress_repository=self.progress_repository,
        slack_notifier=self.slack_notifier,
    )

    result = job.execute()

    logger.info(f"{name} scraping job completed: {{result.status.value}}")
```

3. **分岐追加**
```python
def run_prefecture_scraping(self, prefecture_code: str) -> None:
    # 既存のコードに追加
    elif prefecture_code == "{code}":
        self.run_{english_name}_scraping()
```

### 6. 環境変数の更新

`.env.development`と`.env.example`の`TARGET_PREFECTURES`に都道府県コードを追加：

```bash
# 既存の値に追加
TARGET_PREFECTURES=08,{code}
```

### 7. テスト方法の説明

ユーザーに以下のテスト手順を説明してください：

```bash
# 1. Firestoreエミュレータを起動
make dev-start

# 2. スクレイピングを実行
python scripts/run_scraping.py --prefecture {code} --debug

# 3. Firestore UIでデータ確認
# http://localhost:4000

# 4. TODO コメントを確認して、実際のサイト構造に合わせて調整
```

### 8. 完了メッセージ

すべてのファイルを作成したら、以下のメッセージを表示：

```
✅ {name}のスクレイパーを追加しました！

作成されたファイル：
- src/features/scraping/config/prefectures/{english_name}.yaml
- src/features/scraping/parsers/prefectures/{english_name}_parser.py
- src/features/scraping/scrapers/prefectures/{english_name}.py
- src/features/batch/orchestrator.py（更新）

次のステップ：
1. {name}の子育て支援パスポートサイトを調査
2. {english_name}.yaml の TODO コメントを埋める
3. {english_name}_parser.py のセレクタを調整
4. ローカル環境でテスト実行

詳細は docs/ADD_PREFECTURE_EXAMPLE.md を参照してください。
```

## 注意事項

- すべてのファイルに適切なTODOコメントを含めること
- Firestoreのデータ型（Shopクラス）は共通なので変更不要
- 茨城県スクレイパーを参考実装として使用すること
- セッショントークンの必要性を確認すること