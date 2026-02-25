"""Settings の SecretStr マスキングテスト"""

import warnings

import pytest
from pydantic import SecretStr

from app.config.settings import Settings, get_settings


class TestSettingsSecretStr:
    def test_openai_api_key_is_secret_str_type(self):
        """openai_api_key が SecretStr 型であることを確認"""
        settings = Settings(openai_api_key="sk-test-12345")
        assert isinstance(settings.openai_api_key, SecretStr)

    def test_openai_api_key_masked_in_str(self):
        """str() での表示がマスキングされることを確認"""
        settings = Settings(openai_api_key="sk-test-12345")
        assert "**" in str(settings.openai_api_key)
        assert "sk-test-12345" not in str(settings.openai_api_key)

    def test_openai_api_key_masked_in_repr(self):
        """repr() での表示がマスキングされることを確認"""
        settings = Settings(openai_api_key="sk-test-12345")
        assert "sk-test-12345" not in repr(settings.openai_api_key)

    def test_openai_api_key_get_secret_value_returns_actual_value(self):
        """get_secret_value() が実際の値を返すことを確認"""
        actual_key = "sk-test-12345"
        settings = Settings(openai_api_key=actual_key)
        assert settings.openai_api_key.get_secret_value() == actual_key

    def test_openai_api_key_default_is_empty_secret_str(self):
        """デフォルト値が空の SecretStr であることを確認"""
        settings = Settings()
        assert isinstance(settings.openai_api_key, SecretStr)
        assert settings.openai_api_key.get_secret_value() == ""


class TestJwtSecretKeySecretStr:
    def test_jwt_secret_key_is_secret_str(self):
        """jwt_secret_key が SecretStr 型であることを確認"""
        settings = Settings(jwt_secret_key="my-custom-secret")
        assert isinstance(settings.jwt_secret_key, SecretStr)

    def test_jwt_secret_key_masked_in_str(self):
        """jwt_secret_key が str() でマスキングされることを確認"""
        settings = Settings(jwt_secret_key="my-custom-secret")
        assert "my-custom-secret" not in str(settings.jwt_secret_key)
        assert "**" in str(settings.jwt_secret_key)

    def test_jwt_secret_custom_value_accepted(self):
        """カスタム値の jwt_secret_key が正しく取得できることを確認"""
        settings = Settings(jwt_secret_key="my-super-secret-key")
        assert settings.jwt_secret_key.get_secret_value() == "my-super-secret-key"

    def test_jwt_secret_default_in_production_raises(self):
        """本番モード（debug_mode=False）でデフォルトシークレット使用時に ValueError が発生することを確認"""
        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            Settings(
                jwt_secret_key="dev-secret-key-change-in-production",
                debug_mode=False,
            )

    def test_jwt_secret_default_in_debug_warns(self):
        """デバッグモード（debug_mode=True）でデフォルトシークレット使用時に警告が出ることを確認"""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            settings = Settings(
                jwt_secret_key="dev-secret-key-change-in-production",
                debug_mode=True,
            )
        warning_messages = [str(w.message) for w in caught]
        assert any("JWT_SECRET_KEY" in msg for msg in warning_messages)
        assert isinstance(settings.jwt_secret_key, SecretStr)

    def test_database_url_default_in_production_warns(self, monkeypatch):
        """本番モードでデフォルト database_url 使用時に警告が出ることを確認"""
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            Settings(
                jwt_secret_key="my-safe-secret-key",
                database_url="postgresql://chatbot_user:chatbot_password@localhost:5432/chatbot_db",
                debug_mode=False,
            )
        warning_messages = [str(w.message) for w in caught]
        assert any("DATABASE_URL" in msg for msg in warning_messages)

    def test_get_settings_cache_cleared_after_monkeypatch(self, monkeypatch):
        """get_settings() の lru_cache をクリアして新しい設定が反映されることを確認"""
        get_settings.cache_clear()
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-from-env")
        monkeypatch.setenv("DEBUG_MODE", "true")
        settings = get_settings()
        assert settings.jwt_secret_key.get_secret_value() == "test-secret-from-env"
        get_settings.cache_clear()
