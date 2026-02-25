"""Admin API プロンプト管理エンドポイントのテスト"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.prompt_service import PromptService


@pytest.fixture
def client():
    """テストクライアント"""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """認証ヘッダー"""
    # テスト用トークンを作成
    from app.auth.jwt_handler import create_access_token
    token = create_access_token({"sub": "admin@example.com", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_prompts_data():
    """テスト用のサンプルプロンプトデータ"""
    return {
        "prompts": {
            "system": {
                "id": "system",
                "name": "システムプロンプト",
                "content": "テスト用システムプロンプト",
                "version": 1,
                "updated_at": "2026-02-25T10:00:00Z",
                "history": []
            },
            "category_troubleshooting": {
                "id": "category_troubleshooting",
                "name": "障害・トラブル対応プロンプト",
                "content": "トラブルシューティング用",
                "version": 2,
                "updated_at": "2026-02-25T11:00:00Z",
                "history": [
                    {
                        "version": 1,
                        "content": "初期版",
                        "updated_at": "2026-02-24T10:00:00Z"
                    }
                ]
            }
        }
    }


@pytest.fixture
def temp_prompts_file(tmp_path, sample_prompts_data):
    """一時的なプロンプトファイルを作成"""
    data_file = tmp_path / "prompts.json"
    data_file.write_text(json.dumps(sample_prompts_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data_file


@pytest.fixture
def mock_prompt_service(temp_prompts_file):
    """PromptServiceをモック"""
    PromptService.reset_instance()
    with patch.object(PromptService, "_get_default_data_path", return_value=temp_prompts_file):
        service = PromptService.get_instance()
        yield service
    PromptService.reset_instance()


class TestGetPrompts:
    """GET /api/admin/prompts のテスト"""

    def test_get_prompts_success(self, client, auth_headers, mock_prompt_service):
        """全プロンプト一覧を取得できる"""
        response = client.get("/api/admin/prompts", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["prompts"]) == 2

    def test_get_prompts_unauthorized(self, client):
        """認証なしでは401エラー"""
        response = client.get("/api/admin/prompts")

        assert response.status_code == 401


class TestGetPrompt:
    """GET /api/admin/prompts/{prompt_id} のテスト"""

    def test_get_prompt_success(self, client, auth_headers, mock_prompt_service):
        """個別プロンプトを取得できる"""
        response = client.get("/api/admin/prompts/system", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "system"
        assert data["data"]["name"] == "システムプロンプト"

    def test_get_prompt_not_found(self, client, auth_headers, mock_prompt_service):
        """存在しないプロンプトは404"""
        response = client.get("/api/admin/prompts/nonexistent", headers=auth_headers)

        assert response.status_code == 404

    def test_get_prompt_with_history(self, client, auth_headers, mock_prompt_service):
        """履歴付きプロンプトを取得できる"""
        response = client.get("/api/admin/prompts/category_troubleshooting", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["history"]) == 1


class TestUpdatePrompt:
    """PUT /api/admin/prompts/{prompt_id} のテスト"""

    def test_update_prompt_success(self, client, auth_headers, mock_prompt_service):
        """プロンプトを更新できる"""
        response = client.put(
            "/api/admin/prompts/system",
            headers=auth_headers,
            json={"content": "更新されたコンテンツ"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["content"] == "更新されたコンテンツ"
        assert data["data"]["version"] == 2

    def test_update_prompt_not_found(self, client, auth_headers, mock_prompt_service):
        """存在しないプロンプトの更新は404"""
        response = client.put(
            "/api/admin/prompts/nonexistent",
            headers=auth_headers,
            json={"content": "コンテンツ"}
        )

        assert response.status_code == 404

    def test_update_prompt_invalid_body(self, client, auth_headers, mock_prompt_service):
        """無効なリクエストボディは422"""
        response = client.put(
            "/api/admin/prompts/system",
            headers=auth_headers,
            json={}  # contentがない
        )

        assert response.status_code == 422


class TestRollbackPrompt:
    """POST /api/admin/prompts/{prompt_id}/rollback/{version} のテスト"""

    def test_rollback_prompt_success(self, client, auth_headers, mock_prompt_service):
        """ロールバックできる"""
        response = client.post(
            "/api/admin/prompts/category_troubleshooting/rollback/1",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["content"] == "初期版"
        assert data["data"]["version"] == 3  # 新しいバージョンとして記録

    def test_rollback_prompt_not_found(self, client, auth_headers, mock_prompt_service):
        """存在しないプロンプトのロールバックは404"""
        response = client.post(
            "/api/admin/prompts/nonexistent/rollback/1",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_rollback_version_not_found(self, client, auth_headers, mock_prompt_service):
        """存在しないバージョンのロールバックは404"""
        response = client.post(
            "/api/admin/prompts/system/rollback/99",
            headers=auth_headers
        )

        assert response.status_code == 404


class TestGetPromptHistory:
    """GET /api/admin/prompts/{prompt_id}/history のテスト"""

    def test_get_history_success(self, client, auth_headers, mock_prompt_service):
        """履歴を取得できる"""
        response = client.get(
            "/api/admin/prompts/category_troubleshooting/history",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["history"]) == 1

    def test_get_history_empty(self, client, auth_headers, mock_prompt_service):
        """履歴がない場合は空リスト"""
        response = client.get(
            "/api/admin/prompts/system/history",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["history"] == []

    def test_get_history_prompt_not_found(self, client, auth_headers, mock_prompt_service):
        """存在しないプロンプトの履歴は404"""
        response = client.get(
            "/api/admin/prompts/nonexistent/history",
            headers=auth_headers
        )

        assert response.status_code == 404
