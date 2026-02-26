"""画像解析ツール テストスイート

TDD GREEN フェーズ: analyze_image ツールのテスト
"""

import base64
import pytest
from unittest.mock import patch, MagicMock


class TestImageAnalysisTool:
    """analyze_image ツールのテスト"""

    def test_analyze_image_extracts_error_codes(self):
        """画像からエラーコードを抽出できる"""
        from app.agents.tools.image_analysis import analyze_image

        # モックのLLMレスポンス
        mock_response = MagicMock()
        mock_response.content = '''分析結果:
- エラーコード: [E001, E002]
- UI要素: [ログインボタン, パスワード入力欄]
- テキスト: "ログインに失敗しました"
- 概要: "認証エラーの画面キャプチャです"'''

        with patch("app.agents.tools.image_analysis.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            # ツールのinvokeメソッドを使用
            result = analyze_image.invoke({"image_data": "base64_encoded_image_data"})

            assert "error_codes" in result
            assert "E001" in result["error_codes"]
            assert "ui_elements" in result
            assert "extracted_text" in result

    def test_analyze_image_returns_empty_on_no_errors(self):
        """エラーがない場合は空の結果を返す"""
        from app.agents.tools.image_analysis import analyze_image

        mock_response = MagicMock()
        mock_response.content = '''分析結果:
- エラーコード: []
- UI要素: [メニューバー, 設定アイコン]
- テキスト: "設定"
- 概要: "設定画面のスクリーンショットです"'''

        with patch("app.agents.tools.image_analysis.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            result = analyze_image.invoke({"image_data": "base64_encoded_image_data"})

            assert result["error_codes"] == []
            assert "ui_elements" in result

    def test_analyze_image_handles_invalid_input(self):
        """無効な入力を適切に処理する"""
        from app.agents.tools.image_analysis import analyze_image

        result = analyze_image.invoke({"image_data": ""})

        assert result["error_codes"] == []
        assert result["ui_elements"] == []
        assert result["extracted_text"] == ""
        assert result["summary"] == ""

    def test_analyze_image_uses_vision_model(self):
        """Vision API（GPT-4o）を使用する"""
        from app.agents.tools.image_analysis import analyze_image

        with patch("app.agents.tools.image_analysis.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke = MagicMock(return_value=MagicMock(content="分析結果"))
            mock_get_llm.return_value = mock_llm

            analyze_image.invoke({"image_data": "valid_base64_data"})

            # get_llm が呼ばれたことを確認
            mock_get_llm.assert_called_once()


class TestImageAnalysisIntegration:
    """画像解析の統合テスト"""

    def test_tool_is_registered(self):
        """ツールが__init__.pyにエクスポートされている"""
        from app.agents.tools import analyze_image
        
        assert analyze_image is not None

    def test_tool_has_proper_description(self):
        """ツールに適切な説明がある"""
        from app.agents.tools.image_analysis import analyze_image
        
        # StructuredToolのdescription属性をチェック
        assert analyze_image.description is not None
        assert "画像" in analyze_image.description or "image" in analyze_image.description.lower()
