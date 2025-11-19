# デプロイメントガイド

本番環境とステージング環境へのデプロイ方法を説明します。

## 📋 環境

| 環境 | プロジェクトID | トリガー | デプロイ方法 |
|------|---------------|---------|-------------|
| **Staging** | `iiba-staging` | `main`ブランチへのpush | 自動デプロイ |
| **Production** | `iiba-production` | タグ（`v*.*.*`）のpush | 自動デプロイ + 承認 |

## 🚀 本番環境へのデプロイ

### 前提条件

1. **GitHub Secretsの設定**

   GitHub Actionsで本番環境にデプロイするために、以下のSecretsを設定する必要があります：

   - `GCP_WORKLOAD_IDENTITY_PROVIDER_PROD` - Workload Identity Provider（本番環境用）
   - `GCP_SERVICE_ACCOUNT_PROD` - サービスアカウント（本番環境用）

   設定方法：
   ```bash
   # GitHub Repositoryの Settings → Secrets and variables → Actions → New repository secret
   ```

2. **GitHub Environment**

   本番環境デプロイ時の承認フローを設定するため、Environmentを作成します：

   ```
   Settings → Environments → New environment
   Name: production
   Protection rules:
     ✓ Required reviewers（承認者を設定）
   ```

### 方法1: Makeコマンドでリリース（推奨）

```bash
# 新しいバージョンをリリース
make release VERSION=v1.0.0
```

このコマンドは以下を実行します：
1. タグが既に存在しないか確認
2. 現在のブランチとコミットを表示
3. 確認プロンプトを表示
4. タグを作成してGitHubにpush
5. GitHub Actionsが自動的に本番環境へデプロイ

**出力例：**
```
Creating release v1.0.0...
Current branch: main
Latest commit: abc1234 Add new feature

Create tag v1.0.0 and trigger production deployment? [y/N] y
✓ Tag v1.0.0 created and pushed
✓ GitHub Actions will deploy to production automatically
```

### 方法2: 手動でタグを作成

```bash
# タグを作成
git tag -a v1.0.0 -m "Release v1.0.0"

# タグをpush
git push origin v1.0.0
```

タグがpushされると、GitHub Actionsが自動的に本番環境へデプロイを開始します。

### バージョニング規則

セマンティックバージョニングを使用します：

```
v<メジャー>.<マイナー>.<パッチ>

例:
v1.0.0 - 初回リリース
v1.1.0 - 新機能追加
v1.1.1 - バグフィックス
v2.0.0 - 破壊的変更
```

## 🔄 デプロイフロー

### Staging環境

```
mainブランチへpush
    ↓
GitHub Actions実行
    ↓
1. コードチェックアウト
2. GCP認証
3. Dockerイメージビルド
4. Artifact Registryへpush
5. Cloud Runへデプロイ
    ↓
デプロイ完了
```

### Production環境

```
タグ（v*.*.*）をpush
    ↓
GitHub Actions実行
    ↓
1. コードチェックアウト
2. バージョン抽出
3. GCP認証（本番環境）
4. Dockerイメージビルド（タグ付き）
5. Artifact Registryへpush
6. Cloud Runへデプロイ
7. デプロイmentタグ追加
8. GitHubリリース作成
    ↓
Smoke Test実行
    ↓
1. ヘルスチェック
2. ルートエンドポイントチェック
    ↓
デプロイ完了
```

## 📊 GitHub Actionsの確認

### デプロイ状況の確認

1. GitHubリポジトリの **Actions** タブを開く
2. ワークフロー一覧から **Deploy to Production** を選択
3. 実行状況とログを確認

### デプロイログの確認

```bash
# Cloud Runのログを確認
gcloud run services logs read iiba-kosodate-passport-scraper \
  --project iiba-production \
  --region asia-northeast1 \
  --limit 100
```

## 🔧 手動デプロイ（緊急時）

緊急時に手動でデプロイする場合：

```bash
# 本番環境へ手動デプロイ（要確認プロンプト）
make deploy-production VERSION=v1.0.0
```

このコマンドは確認プロンプトを表示し、本番環境へ直接デプロイします。

**⚠️ 注意**: 通常は`make release`を使用して、GitHub Actions経由でデプロイしてください。

## 🧪 デプロイ前のチェックリスト

本番環境へデプロイする前に、以下を確認してください：

- [ ] すべてのテストが通過している
- [ ] Staging環境で動作確認済み
- [ ] コードレビューが完了している
- [ ] CHANGELOG.mdが更新されている
- [ ] 破壊的変更がある場合、ドキュメントが更新されている
- [ ] データベースマイグレーションが必要な場合、準備が完了している

## 🔍 デプロイ後の確認

デプロイ後は以下を確認してください：

### 1. ヘルスチェック

```bash
# Staging
curl https://iiba-kosodate-passport-scraper-62611089199.asia-northeast1.run.app/health

# Production
curl https://iiba-kosodate-passport-scraper-production.a.run.app/health
```

期待されるレスポンス：
```json
{"status":"healthy"}
```

### 2. サービス情報の確認

```bash
# Production環境のサービス情報を確認
gcloud run services describe iiba-kosodate-passport-scraper \
  --project iiba-production \
  --region asia-northeast1 \
  --format='table(status.url,status.latestReadyRevisionName,spec.template.spec.containers[0].image)'
```

### 3. 動作確認

```bash
# スクレイピングジョブのテスト実行
curl -X POST "https://<service-url>/scrape/08"
```

### 4. ログの監視

```bash
# リアルタイムでログを監視
gcloud run services logs tail iiba-kosodate-passport-scraper \
  --project iiba-production \
  --region asia-northeast1
```

## 🔙 ロールバック

問題が発生した場合、以下の方法でロールバックできます：

### 方法1: 以前のリビジョンへ切り替え

```bash
# リビジョン一覧を表示
gcloud run revisions list \
  --service iiba-kosodate-passport-scraper \
  --project iiba-production \
  --region asia-northeast1

# 特定のリビジョンへトラフィックを100%ルーティング
gcloud run services update-traffic iiba-kosodate-passport-scraper \
  --project iiba-production \
  --region asia-northeast1 \
  --to-revisions <前のリビジョン名>=100
```

### 方法2: 以前のタグで再デプロイ

```bash
# 正常に動作していたバージョンで再デプロイ
make deploy-production VERSION=v1.0.0
```

## 📈 本番環境の設定

### リソース設定

| 項目 | Staging | Production |
|------|---------|------------|
| Memory | 1Gi | 2Gi |
| CPU | 1 | 2 |
| Timeout | 3600s | 3600s |
| Min Instances | 0 | 0 |
| Max Instances | 10 | 20 |

### 環境変数

```bash
ENVIRONMENT=production
GCP_PROJECT_ID=iiba-production
FIRESTORE_DATABASE_ID=(default)
GCS_BUCKET_NAME=iiba-production-kosodate-scraper
TARGET_PREFECTURES=08
```

## 🔐 必要な権限

### GCPサービスアカウント

本番環境のサービスアカウントには以下の権限が必要です：

- `roles/run.admin` - Cloud Runサービスの管理
- `roles/iam.serviceAccountUser` - サービスアカウントとしての実行
- `roles/datastore.user` - Firestoreへのアクセス
- `roles/storage.admin` - Cloud Storageへのアクセス
- `roles/secretmanager.secretAccessor` - Secret Managerへのアクセス

### GitHub Actions

Workload Identity Federationを使用してGCPへ認証します。

設定手順：
```bash
# Workload Identity Poolの作成（既存の場合はスキップ）
gcloud iam workload-identity-pools create "github-actions" \
  --project="iiba-production" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# Workload Identity Providerの作成
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="iiba-production" \
  --location="global" \
  --workload-identity-pool="github-actions" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# サービスアカウントへの権限付与
gcloud iam service-accounts add-iam-policy-binding "<service-account>@iiba-production.iam.gserviceaccount.com" \
  --project="iiba-production" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/<project-number>/locations/global/workloadIdentityPools/github-actions/attribute.repository/<org>/<repo>"
```

## 📚 参考資料

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [Semantic Versioning](https://semver.org/)

## 🆘 トラブルシューティング

### デプロイが失敗する

1. GitHub Actionsのログを確認
2. GCP認証エラーの場合、Secretsを確認
3. イメージビルドエラーの場合、Dockerfileを確認

### ヘルスチェックが失敗する

1. Cloud Runのログを確認
2. 環境変数が正しく設定されているか確認
3. Firestoreへの接続を確認

### ロールバックが必要

上記「ロールバック」セクションを参照してください。

## 📞 サポート

問題が解決しない場合：
1. GitHub Issuesで報告
2. Cloud Runのログを添付
3. エラーメッセージを記載
