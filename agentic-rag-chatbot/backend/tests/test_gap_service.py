import pytest
from httpx import AsyncClient, ASGITransport

from app.auth.jwt_handler import create_access_token
from app.main import app
from app.services.gap_service import KnowledgeGapService


@pytest.fixture(autouse=True)
def reset_gap_service(tmp_path):
    """各テスト後にシングルトンをリセットしてクリーンな状態を保つ"""
    KnowledgeGapService.reset_instance()
    # tmpディレクトリのパスで新しいインスタンスを初期化
    instance = KnowledgeGapService(persist_path=str(tmp_path / "test_gaps.json"))
    KnowledgeGapService._instance = instance
    yield
    KnowledgeGapService.reset_instance()


class TestKnowledgeGapService:
    def test_record_gap_basic(self):
        """record_gap が正しくギャップを記録する"""
        service = KnowledgeGapService.get_instance()
        service.record_gap(query="テスト質問", category="技術", reason="情報が不足")

        gaps = service.get_gaps()
        assert len(gaps) == 1
        assert gaps[0]["query"] == "テスト質問"
        assert gaps[0]["category"] == "技術"
        assert gaps[0]["reason"] == "情報が不足"
        assert "timestamp" in gaps[0]

    def test_record_gap_default_values(self):
        """record_gap のデフォルト値が正しく設定される"""
        service = KnowledgeGapService.get_instance()
        service.record_gap(query="質問のみ")

        gaps = service.get_gaps()
        assert len(gaps) == 1
        assert gaps[0]["category"] == ""
        assert gaps[0]["reason"] == ""

    def test_get_gaps_sorted_newest_first(self):
        """get_gaps が新しい順に返す"""
        service = KnowledgeGapService.get_instance()
        service.record_gap(query="古い質問")
        service.record_gap(query="新しい質問")

        gaps = service.get_gaps()
        assert len(gaps) == 2
        assert gaps[0]["query"] == "新しい質問"
        assert gaps[1]["query"] == "古い質問"

    def test_get_gaps_limit(self):
        """get_gaps の limit パラメータが機能する"""
        service = KnowledgeGapService.get_instance()
        for i in range(5):
            service.record_gap(query=f"質問{i}")

        gaps = service.get_gaps(limit=3)
        assert len(gaps) == 3

    def test_get_summary_total(self):
        """get_summary のtotal集計が正しい"""
        service = KnowledgeGapService.get_instance()
        service.record_gap(query="質問1")
        service.record_gap(query="質問2")
        service.record_gap(query="質問3")

        summary = service.get_summary()
        assert summary["total"] == 3

    def test_get_summary_by_category(self):
        """get_summary のカテゴリ別集計が正しい"""
        service = KnowledgeGapService.get_instance()
        service.record_gap(query="質問1", category="技術")
        service.record_gap(query="質問2", category="技術")
        service.record_gap(query="質問3", category="ビジネス")

        summary = service.get_summary()
        assert summary["by_category"]["技術"] == 2
        assert summary["by_category"]["ビジネス"] == 1

    def test_get_summary_empty_category(self):
        """カテゴリが空の場合の集計が正しい"""
        service = KnowledgeGapService.get_instance()
        service.record_gap(query="カテゴリなし質問")

        summary = service.get_summary()
        assert summary["by_category"][""] == 1

    def test_persistence(self, tmp_path):
        """ファイルへの永続化が正しく機能する"""
        persist_file = tmp_path / "persist_test.json"
        service1 = KnowledgeGapService(persist_path=str(persist_file))
        service1.record_gap(query="永続化テスト", reason="テスト理由")

        # 別インスタンスで読み込んで検証
        service2 = KnowledgeGapService(persist_path=str(persist_file))
        gaps = service2.get_gaps()
        assert len(gaps) == 1
        assert gaps[0]["query"] == "永続化テスト"

    def test_singleton_pattern(self):
        """シングルトンパターンが正しく機能する"""
        service1 = KnowledgeGapService.get_instance()
        service2 = KnowledgeGapService.get_instance()
        assert service1 is service2

    def test_immutability_of_gaps_list(self):
        """record_gap が元のリストを変更しない（イミュータブルパターン）"""
        service = KnowledgeGapService.get_instance()
        original_gaps = service._gaps
        service.record_gap(query="新しい質問")
        # 新しいリストが作成されていることを確認
        assert service._gaps is not original_gaps


@pytest.mark.asyncio
class TestAdminApiEndpoints:
    async def test_get_knowledge_gaps_authenticated(self):
        """認証付きで GET /api/admin/knowledge-gaps が正常に動作する"""
        token = create_access_token({"sub": "admin-user"})
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/admin/knowledge-gaps", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "gaps" in data["data"]
        assert "summary" in data["data"]

    async def test_get_knowledge_gaps_unauthenticated(self):
        """認証なしで GET /api/admin/knowledge-gaps が 401 を返す"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/admin/knowledge-gaps")

        assert response.status_code == 401

    async def test_get_knowledge_gaps_invalid_token(self):
        """無効なトークンで 403 が返る"""
        headers = {"Authorization": "Bearer invalid.token.here"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/admin/knowledge-gaps", headers=headers)

        assert response.status_code == 403

    async def test_get_knowledge_gaps_returns_recorded_gaps(self):
        """記録されたギャップがエンドポイントから取得できる"""
        service = KnowledgeGapService.get_instance()
        service.record_gap(query="テストAPIギャップ", category="API", reason="APIテスト用")

        token = create_access_token({"sub": "admin-user"})
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/admin/knowledge-gaps", headers=headers)

        assert response.status_code == 200
        data = response.json()
        gaps = data["data"]["gaps"]
        assert len(gaps) >= 1
        queries = [g["query"] for g in gaps]
        assert "テストAPIギャップ" in queries

    async def test_get_knowledge_gaps_with_limit(self):
        """limit パラメータが正しく機能する"""
        service = KnowledgeGapService.get_instance()
        for i in range(5):
            service.record_gap(query=f"ギャップ{i}")

        token = create_access_token({"sub": "admin-user"})
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/admin/knowledge-gaps?limit=3", headers=headers
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["gaps"]) <= 3
