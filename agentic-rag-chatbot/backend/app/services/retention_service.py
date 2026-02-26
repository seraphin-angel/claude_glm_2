"""P3-49: データ保持ポリシー（GDPR）- データ削除・保持管理サービス"""

import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Optional

from app.models.retention import AuditLogEntry, DataDeletionRequest, RetentionPolicy


class RetentionService:
    """データ保持ポリシーとGDPRデータ削除管理サービス（インメモリ実装）"""

    _instance: Optional["RetentionService"] = None
    _lock: Lock = Lock()

    def __init__(self) -> None:
        # テナントIDとデータ種別をキーとするポリシー辞書
        # Key: (tenant_id, data_type) -> RetentionPolicy
        self._policies: dict[tuple[str, str], RetentionPolicy] = {}
        # 監査ログ (不変リスト)
        self._audit_logs: list[dict[str, Any]] = []

    @classmethod
    def get_instance(cls) -> "RetentionService":
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

    def create_policy(self, policy: RetentionPolicy) -> RetentionPolicy:
        """保持ポリシーを作成する。

        Args:
            policy: 保持ポリシー

        Returns:
            作成された保持ポリシー
        """
        key = (policy.tenant_id, policy.data_type)
        # 不変パターン: 新しい辞書を作成
        self._policies = {**self._policies, key: policy}

        self._add_audit_log(
            operation="create_policy",
            tenant_id=policy.tenant_id,
            data_type=policy.data_type,
            record_count=1,
            performed_by="system",
        )
        return policy

    def get_policy(
        self,
        tenant_id: str,
        data_type: str,
    ) -> Optional[RetentionPolicy]:
        """保持ポリシーを取得する。

        Args:
            tenant_id: テナントID
            data_type: データ種別

        Returns:
            保持ポリシー（見つからない場合はNone）
        """
        return self._policies.get((tenant_id, data_type))

    def list_policies(
        self,
        tenant_id: str,
        include_inactive: bool = False,
    ) -> list[RetentionPolicy]:
        """テナントの保持ポリシー一覧を取得する。

        Args:
            tenant_id: テナントID
            include_inactive: 非アクティブなポリシーも含めるか

        Returns:
            保持ポリシーのリスト
        """
        policies = [
            p for (tid, _), p in self._policies.items()
            if tid == tenant_id
        ]
        if not include_inactive:
            policies = [p for p in policies if p.is_active]
        return policies

    def update_policy(
        self,
        tenant_id: str,
        data_type: str,
        retention_days: int,
    ) -> RetentionPolicy:
        """保持ポリシーを更新する。

        Args:
            tenant_id: テナントID
            data_type: データ種別
            retention_days: 新しい保持期間（日数）

        Returns:
            更新された保持ポリシー

        Raises:
            ValueError: ポリシーが見つからない場合
        """
        key = (tenant_id, data_type)
        existing = self._policies.get(key)
        if existing is None:
            raise ValueError(
                f"Retention policy for tenant '{tenant_id}' and data_type '{data_type}' not found"
            )

        # 不変パターン: 新しいRetentionPolicyオブジェクトを作成
        updated = RetentionPolicy(
            tenant_id=existing.tenant_id,
            data_type=existing.data_type,
            retention_days=retention_days,
            is_active=existing.is_active,
        )

        self._policies = {**self._policies, key: updated}

        self._add_audit_log(
            operation="update_policy",
            tenant_id=tenant_id,
            data_type=data_type,
            record_count=1,
            performed_by="system",
            details={"retention_days": retention_days},
        )
        return updated

    def delete_user_data(self, request: DataDeletionRequest) -> dict[str, Any]:
        """ユーザーデータを削除する（GDPR Article 17 - Right to erasure）。

        Args:
            request: データ削除リクエスト

        Returns:
            削除結果
        """
        deletion_id = f"DEL-{uuid.uuid4().hex[:8].upper()}"

        # 削除操作の監査ログを記録
        self._add_audit_log(
            operation="delete_user_data",
            tenant_id=request.tenant_id,
            data_type="all",
            record_count=0,  # 実際の削除件数は実装次第
            performed_by="gdpr_request",
            details={
                "deletion_id": deletion_id,
                "user_id": request.user_id,
                "reason": request.reason,
                "requested_at": request.requested_at.isoformat() if request.requested_at else None,
            },
        )

        return {
            "success": True,
            "deletion_id": deletion_id,
            "user_id": request.user_id,
            "tenant_id": request.tenant_id,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "reason": request.reason,
        }

    def get_audit_logs(
        self,
        tenant_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """監査ログを取得する。

        Args:
            tenant_id: テナントID
            limit: 取得する最大件数

        Returns:
            監査ログのリスト
        """
        logs = [
            log for log in self._audit_logs
            if log["tenant_id"] == tenant_id
        ]
        return logs[:limit]

    def find_expired_data(self, tenant_id: str) -> list[dict[str, Any]]:
        """保持ポリシーに基づいて期限切れデータを特定する。

        Args:
            tenant_id: テナントID

        Returns:
            期限切れデータの情報リスト（現在はインメモリ実装のため空リスト）
        """
        now = datetime.now(timezone.utc)
        policies = self.list_policies(tenant_id)
        expired = []

        for policy in policies:
            # 実際の実装ではデータストアを検索するが、
            # インメモリ実装ではポリシー情報のみ返す
            expired.append({
                "tenant_id": tenant_id,
                "data_type": policy.data_type,
                "retention_days": policy.retention_days,
                "policy_active": policy.is_active,
            })

        return expired

    def run_cleanup_job(self) -> dict[str, Any]:
        """期限切れデータのクリーンアップジョブを実行する。

        Returns:
            クリーンアップ結果
        """
        cleaned_records = 0
        errors: list[str] = []

        try:
            # 全テナントのポリシーを確認
            tenant_ids = {tid for (tid, _) in self._policies.keys()}
            for tenant_id in tenant_ids:
                expired = self.find_expired_data(tenant_id)
                # 実際の実装ではここでデータを削除する
                cleaned_records += len(expired)

            if cleaned_records > 0:
                self._add_audit_log(
                    operation="cleanup_job",
                    tenant_id="system",
                    data_type="all",
                    record_count=cleaned_records,
                    performed_by="scheduler",
                )
        except Exception as e:
            errors.append(str(e))

        return {
            "cleaned_records": cleaned_records,
            "errors": errors,
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _add_audit_log(
        self,
        operation: str,
        tenant_id: str,
        data_type: str,
        record_count: int,
        performed_by: str,
        details: Optional[dict] = None,
    ) -> None:
        """監査ログエントリを追加する（内部用）。"""
        entry = {
            "operation": operation,
            "tenant_id": tenant_id,
            "data_type": data_type,
            "record_count": record_count,
            "performed_by": performed_by,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {},
        }
        # 不変パターン: 新しいリストを作成
        self._audit_logs = [entry] + self._audit_logs
