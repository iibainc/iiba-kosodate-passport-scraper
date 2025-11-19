# Claude Code Skills

このプロジェクトで使用できるClaude Codeのスキル一覧です。

## スキルの使い方

スキルを実行するには、以下のいずれかの方法を使用します：

### 方法1: @スキル名

```
@add-prefecture
```

### 方法2: 自然言語

```
新しい都道府県を追加して
```

Claude Codeが自動的に適切なスキルを選択して実行します。

---

## 利用可能なスキル

### 📍 add-prefecture

新しい都道府県のスクレイパーを追加します。

**実行コマンド:**
```
@add-prefecture
```

**機能:**
- 都道府県情報（名前、コード、英語名）を対話的に取得
- 3つのファイル（設定、パーサー、スクレイパー）を自動生成
- オーケストレーターを自動更新
- TODOコメントを含めた完全なテンプレートを作成
- テスト方法の説明

**作成されるファイル:**
- `src/features/scraping/config/prefectures/{english_name}.yaml`
- `src/features/scraping/parsers/prefectures/{english_name}_parser.py`
- `src/features/scraping/scrapers/prefectures/{english_name}.py`
- `src/features/batch/orchestrator.py`（更新）
- `.env.development`（更新）
- `.env.example`（更新）

**使用例:**
```
ユーザー: @add-prefecture

Claude: 追加する都道府県名を教えてください（例: 東京都）
ユーザー: 東京都

Claude: 都道府県コードを教えてください（例: 13）
ユーザー: 13

Claude: 英語名を教えてください（例: tokyo）
ユーザー: tokyo

Claude: ✅ 東京都のスクレイパーを追加しました！
（ファイル作成と説明）
```

**次のステップ:**
1. 都道府県の子育て支援パスポートサイトを調査
2. `{english_name}.yaml`のTODOコメントを埋める
3. `{english_name}_parser.py`のセレクタを実際のHTMLに合わせる
4. ローカル環境でテスト実行

**参考ドキュメント:**
- [新しい都道府県の追加方法](../docs/ADD_PREFECTURE_EXAMPLE.md)
- [茨城県スクレイパー](../src/features/scraping/scrapers/prefectures/ibaraki.py)（参考実装）

---

## スキルのカスタマイズ

新しいスキルを追加する場合は、`.claude/skills/`ディレクトリに新しいマークダウンファイルを作成してください。

**スキルファイルの構造:**
```markdown
# スキル名

説明

## 実行方法

@スキル名

## タスク

1. タスク1
2. タスク2
...
```

詳細は[Claude Code公式ドキュメント](https://code.claude.com/)を参照してください。

---

## トラブルシューティング

### スキルが認識されない

1. `.claude/skills/`ディレクトリにファイルが存在するか確認
2. ファイル名が`.md`で終わっているか確認
3. Claude Codeを再起動

### スキルが期待通りに動作しない

1. スキルファイルの内容を確認
2. マークダウンの構文が正しいか確認
3. タスクの指示が明確か確認
