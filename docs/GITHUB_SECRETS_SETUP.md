# GitHub Secrets セットアップガイド

GitHub ActionsでGCPへデプロイするために必要なSecretsの設定方法を説明します。

## 📋 必要なSecrets

### Staging環境

| Secret名 | 説明 | 取得方法 |
|---------|------|---------|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Workload Identity Provider | 下記手順で取得 |
| `GCP_SERVICE_ACCOUNT` | サービスアカウントEmail | `<sa-name>@iiba-staging.iam.gserviceaccount.com` |

### Production環境

| Secret名 | 説明 | 取得方法 |
|---------|------|---------|
| `GCP_WORKLOAD_IDENTITY_PROVIDER_PROD` | Workload Identity Provider（本番） | 下記手順で取得 |
| `GCP_SERVICE_ACCOUNT_PROD` | サービスアカウントEmail（本番） | `<sa-name>@iiba-production.iam.gserviceaccount.com` |

## 🔧 セットアップ手順

### 1. Workload Identity Federationの設定

#### Staging環境

```bash
PROJECT_ID="iiba-staging"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
REPO="<GitHub組織名>/<リポジトリ名>"  # 例: your-org/iiba-kosodate-passport-scraper

# 1. Workload Identity Poolの作成
gcloud iam workload-identity-pools create "github-actions" \
  --project="$PROJECT_ID" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# 2. Workload Identity Providerの作成
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="$PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="github-actions" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# 3. サービスアカウントの作成
gcloud iam service-accounts create kosodate-scraper-sa \
  --display-name="Kosodate Scraper Service Account" \
  --project="$PROJECT_ID"

SA_EMAIL="kosodate-scraper-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# 4. サービスアカウントへの権限付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

# 5. Workload Identity Federationの紐付け
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions/attribute.repository/${REPO}"

# 6. Workload Identity Provider URIの取得（これをGitHub Secretsに設定）
echo "GCP_WORKLOAD_IDENTITY_PROVIDER:"
echo "projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions/providers/github-provider"

echo ""
echo "GCP_SERVICE_ACCOUNT:"
echo "${SA_EMAIL}"
```

#### Production環境

```bash
PROJECT_ID="iiba-production"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
REPO="<GitHub組織名>/<リポジトリ名>"

# 1. Workload Identity Poolの作成
gcloud iam workload-identity-pools create "github-actions" \
  --project="$PROJECT_ID" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# 2. Workload Identity Providerの作成
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="$PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="github-actions" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# 3. サービスアカウントの作成
gcloud iam service-accounts create kosodate-scraper-sa \
  --display-name="Kosodate Scraper Service Account (Production)" \
  --project="$PROJECT_ID"

SA_EMAIL="kosodate-scraper-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# 4. サービスアカウントへの権限付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

# 5. Workload Identity Federationの紐付け
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions/attribute.repository/${REPO}"

# 6. Workload Identity Provider URIの取得（これをGitHub Secretsに設定）
echo "GCP_WORKLOAD_IDENTITY_PROVIDER_PROD:"
echo "projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions/providers/github-provider"

echo ""
echo "GCP_SERVICE_ACCOUNT_PROD:"
echo "${SA_EMAIL}"
```

### 2. GitHub Secretsの設定

1. GitHubリポジトリページを開く
2. **Settings** → **Secrets and variables** → **Actions** をクリック
3. **New repository secret** をクリック
4. 以下のSecretsを追加：

#### Staging環境用

**Name**: `GCP_WORKLOAD_IDENTITY_PROVIDER`
**Value**:
```
projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-actions/providers/github-provider
```

**Name**: `GCP_SERVICE_ACCOUNT`
**Value**:
```
kosodate-scraper-sa@iiba-staging.iam.gserviceaccount.com
```

#### Production環境用

**Name**: `GCP_WORKLOAD_IDENTITY_PROVIDER_PROD`
**Value**:
```
projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-actions/providers/github-provider
```

**Name**: `GCP_SERVICE_ACCOUNT_PROD`
**Value**:
```
kosodate-scraper-sa@iiba-production.iam.gserviceaccount.com
```

### 3. GitHub Environment設定（本番環境のみ）

本番環境へのデプロイ時に承認を必要とする場合：

1. **Settings** → **Environments** をクリック
2. **New environment** をクリック
3. **Name**: `production` を入力
4. **Configure environment** をクリック
5. **Required reviewers** にチェックを入れる
6. 承認者を追加（最大6人）
7. **Save protection rules** をクリック

これにより、本番環境へのデプロイ前に承認が必要になります。

## ✅ 設定の確認

### 手動でGitHub Actionsを実行してテスト

1. **Actions** タブを開く
2. **Deploy to Staging** ワークフローを選択
3. **Run workflow** をクリック
4. ログを確認して、認証とデプロイが成功するか確認

### トラブルシューティング

#### 認証エラー

```
Error: google-github-actions/auth failed with: retry function failed after 1 attempt(s)
```

**解決策**:
1. Workload Identity Provider URIが正しいか確認
2. サービスアカウントEmailが正しいか確認
3. Workload Identity Federationの紐付けが完了しているか確認

```bash
# 紐付けを確認
gcloud iam service-accounts get-iam-policy <SA_EMAIL> --project=<PROJECT_ID>
```

#### 権限エラー

```
Error: Permission denied while using the Cloud Run Admin API.
```

**解決策**:
サービスアカウントに必要な権限が付与されているか確認：

```bash
# 権限を確認
gcloud projects get-iam-policy <PROJECT_ID> \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:<SA_EMAIL>"
```

必要に応じて権限を追加：

```bash
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:<SA_EMAIL>" \
  --role="roles/run.admin"
```

## 🔐 セキュリティベストプラクティス

1. **最小権限の原則**: 必要最小限の権限のみ付与
2. **環境の分離**: Staging/Productionで異なるサービスアカウントを使用
3. **監査ログ**: Cloud Audit Logsを有効化
4. **定期的な確認**: 不要な権限がないか定期的に確認

## 📚 参考資料

- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [GitHub Actions: google-github-actions/auth](https://github.com/google-github-actions/auth)
- [IAM Roles for Cloud Run](https://cloud.google.com/run/docs/reference/iam/roles)
