"""Settings の SecretStr マスキングテスト"""

from pydantic import SecretStr

from app.config.settings import Settings


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
