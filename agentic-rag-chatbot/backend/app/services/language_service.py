"""言語検出サービス

langdetectライブラリを使用してテキストの言語を検出する。
"""

from typing import Optional

from langdetect import detect, LangDetectException

from app.core.logging import get_logger

logger = get_logger(__name__)

# サポートする言語
SUPPORTED_LANGUAGES = {"ja", "en"}
DEFAULT_LANGUAGE = "ja"


class LanguageService:
    """言語検出サービス

    シングルトンパターンで実装され、テキストの言語を検出する。
    """

    _instance: Optional["LanguageService"] = None

    # サポートする言語
    SUPPORTED_LANGUAGES = {"ja", "en"}
    DEFAULT_LANGUAGE = "ja"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def detect(self, text: str) -> str:
        """テキストの言語を検出する

        Args:
            text: 検出対象のテキスト

        Returns:
            言語コード（"ja" または "en"）
        """
        if not text or len(text.strip()) < 3:
            # 短すぎるテキストはデフォルト言語を返す
            return self.DEFAULT_LANGUAGE

        try:
            detected = detect(text)

            # サポート対象外の言語の場合はデフォルト
            if detected not in self.SUPPORTED_LANGUAGES:
                logger.debug(
                    "Detected unsupported language",
                    extra={"detected": detected, "fallback": self.DEFAULT_LANGUAGE},
                )
                return self.DEFAULT_LANGUAGE

            return detected

        except LangDetectException as e:
            logger.warning(
                "Language detection failed",
                extra={"error": str(e), "fallback": self.DEFAULT_LANGUAGE},
            )
            return self.DEFAULT_LANGUAGE

    def get_supported_languages(self) -> list[str]:
        """サポートする言語一覧を取得する

        Returns:
            サポートする言語コードのリスト
        """
        return list(self.SUPPORTED_LANGUAGES)


def get_language_service() -> LanguageService:
    """LanguageServiceのシングルトンインスタンスを取得する

    Returns:
        LanguageServiceインスタンス
    """
    return LanguageService()
