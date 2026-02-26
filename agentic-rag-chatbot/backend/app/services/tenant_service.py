"""P3-48: マルチテナント対応 - テナントサービス（CRUD管理）"""

from threading import Lock
from typing import Optional

from app.models.tenant import Tenant, TenantConfig, TenantCreateRequest


class TenantService:
    """テナントのCRUD管理サービス（インメモリ実装）"""

    _instance: Optional["TenantService"] = None
    _lock: Lock = Lock()

    def __init__(self) -> None:
        # テナントIDをキーとする不変辞書として管理
        self._tenants: dict[str, Tenant] = {}

    @classmethod
    def get_instance(cls) -> "TenantService":
        """シングルトンインスタンスを取得する。"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """シングルトンをリセットする（テスト用）。"""
        with cls._lock:
            cls._instance = None

    def create_tenant(self, request: TenantCreateRequest) -> Tenant:
        """テナントを作成する。

        Args:
            request: テナント作成リクエスト

        Returns:
            作成されたテナント

        Raises:
            ValueError: 同じtenant_idが既に存在する場合
        """
        if request.tenant_id in self._tenants:
            raise ValueError(
                f"Tenant with id '{request.tenant_id}' already exists"
            )

        tenant = Tenant(
            tenant_id=request.tenant_id,
            name=request.name,
            config=request.config,
            is_active=True,
        )

        # 不変パターン: 新しい辞書を作成
        self._tenants = {**self._tenants, request.tenant_id: tenant}
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """テナントを取得する。

        Args:
            tenant_id: テナントID

        Returns:
            テナント（見つからない場合はNone）
        """
        return self._tenants.get(tenant_id)

    def list_tenants(self, include_inactive: bool = False) -> list[Tenant]:
        """テナント一覧を取得する。

        Args:
            include_inactive: 非アクティブなテナントも含めるか

        Returns:
            テナントのリスト
        """
        tenants = list(self._tenants.values())
        if not include_inactive:
            tenants = [t for t in tenants if t.is_active]
        return tenants

    def deactivate_tenant(self, tenant_id: str) -> Tenant:
        """テナントを無効化する。

        Args:
            tenant_id: テナントID

        Returns:
            更新されたテナント

        Raises:
            ValueError: テナントが見つからない場合
        """
        existing = self._tenants.get(tenant_id)
        if existing is None:
            raise ValueError(f"Tenant '{tenant_id}' not found")

        # 不変パターン: 新しいTenantオブジェクトを作成
        updated = Tenant(
            tenant_id=existing.tenant_id,
            name=existing.name,
            config=existing.config,
            is_active=False,
        )

        self._tenants = {**self._tenants, tenant_id: updated}
        return updated

    def validate_tenant(self, tenant_id: str) -> bool:
        """テナントがアクティブかどうかを検証する。

        Args:
            tenant_id: テナントID

        Returns:
            テナントが存在してアクティブな場合はTrue
        """
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            return False
        return tenant.is_active

    def update_tenant_config(
        self,
        tenant_id: str,
        config: TenantConfig,
    ) -> Tenant:
        """テナント設定を更新する。

        Args:
            tenant_id: テナントID
            config: 新しい設定

        Returns:
            更新されたテナント

        Raises:
            ValueError: テナントが見つからない場合
        """
        existing = self._tenants.get(tenant_id)
        if existing is None:
            raise ValueError(f"Tenant '{tenant_id}' not found")

        # 不変パターン: 新しいTenantオブジェクトを作成
        updated = Tenant(
            tenant_id=existing.tenant_id,
            name=existing.name,
            config=config,
            is_active=existing.is_active,
        )

        self._tenants = {**self._tenants, tenant_id: updated}
        return updated
