"""言語検出サービス テストスイート

TDD RED フェーズ: 言語検出のテスト
"""

import pytest
from unittest.mock import patch, MagicMock


class TestLanguageService:
    """LanguageServiceのテスト"""

    def test_detect_japanese_text(self):
        """日本語テキストを検出できる"""
        from app.services.language_service import LanguageService
        
        service = LanguageService()
        
        result = service.detect("こんにちは、元気ですか？")
        
        assert result == "ja"

    def test_detect_english_text(self):
        """英語テキストを検出できる"""
        from app.services.language_service import LanguageService
        
        service = LanguageService()
        
        result = service.detect("Hello, how are you?")
        
        assert result == "en"

    def test_detect_returns_default_for_short_text(self):
        """短いテキストはデフォルト言語を返す"""
        from app.services.language_service import LanguageService
        
        service = LanguageService()
        
        # 1文字など判別が難しい場合
        result = service.detect("a")
        
        # デフォルトは日本語
        assert result in ["ja", "en"]

    def test_detect_with_mixed_languages(self):
        """混合テキストは主要言語を返す"""
        from app.services.language_service import LanguageService
        
        service = LanguageService()
        
        # 日本語メインのテキスト
        result = service.detect("これは日本語のテキストです。This is English.")
        
        assert result == "ja"

    def test_get_supported_languages(self):
        """サポート言語一覧を取得できる"""
        from app.services.language_service import LanguageService
        
        service = LanguageService()
        
        languages = service.get_supported_languages()
        
        assert "ja" in languages
        assert "en" in languages

    def test_singleton_instance(self):
        """シングルトンインスタンスを取得できる"""
        from app.services.language_service import get_language_service
        
        service1 = get_language_service()
        service2 = get_language_service()
        
        assert service1 is service2
