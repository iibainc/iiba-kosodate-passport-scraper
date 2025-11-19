"""GCP Secret Manager連携"""
from typing import Optional

from google.cloud import secretmanager

from ...shared.exceptions.errors import ConfigurationError
from ...shared.logging.config import get_logger

logger = get_logger(__name__)


class SecretManagerClient:
    """Secret Managerクライアント"""

    def __init__(self, project_id: str):
        """
        Args:
            project_id: GCPプロジェクトID
        """
        self.project_id = project_id
        self.client = secretmanager.SecretManagerServiceClient()

    def get_secret(self, secret_name: str, version: str = "latest") -> str:
        """
        シークレットの値を取得

        Args:
            secret_name: シークレット名
            version: バージョン（デフォルト: latest）

        Returns:
            シークレットの値

        Raises:
            ConfigurationError: シークレット取得失敗時
        """
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"
            logger.debug(f"Fetching secret: {name}")

            response = self.client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")

            logger.info(f"Successfully fetched secret: {secret_name}")
            return secret_value

        except Exception as e:
            logger.error(f"Failed to fetch secret {secret_name}: {e}")
            raise ConfigurationError(f"Failed to fetch secret {secret_name}: {e}") from e

    def get_secret_or_none(self, secret_name: str, version: str = "latest") -> Optional[str]:
        """
        シークレットの値を取得（失敗時はNoneを返す）

        Args:
            secret_name: シークレット名
            version: バージョン

        Returns:
            シークレットの値、または None
        """
        try:
            return self.get_secret(secret_name, version)
        except ConfigurationError:
            logger.warning(f"Secret {secret_name} not found, returning None")
            return None
