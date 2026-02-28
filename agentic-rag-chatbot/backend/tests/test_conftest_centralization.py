"""conftest.pyの一元管理を検証するテスト"""

import ast
import os
from pathlib import Path


class TestConftestCentralization:
    """テスト設定の一元管理を検証"""

    def test_conftest_has_jwt_secret(self):
        """conftest.pyにJWT_SECRET_KEYが設定されている"""
        conftest_path = Path(__file__).parent / "conftest.py"
        content = conftest_path.read_text()
        assert 'JWT_SECRET_KEY' in content
        assert 'test-secret-key-for-pytest-only' in content

    def test_conftest_has_debug_mode(self):
        """conftest.pyにDEBUG_MODEが設定されている"""
        conftest_path = Path(__file__).parent / "conftest.py"
        content = conftest_path.read_text()
        assert 'DEBUG_MODE' in content
        assert 'true' in content

    def test_no_duplicate_jwt_secret_in_experiment_tests(self):
        """test_experiment_api.pyに重複したJWT設定がない"""
        test_file = Path(__file__).parent / "test_experiment_api.py"
        content = test_file.read_text()
        # ファイル先頭のos.environ.setdefaultを許可しない（conftest.pyで一元管理）
        lines = content.split('\n')
        import_section_ended = False
        for i, line in enumerate(lines):
            if not import_section_ended and ('def ' in line or 'class ' in line):
                import_section_ended = True
            if not import_section_ended and 'os.environ.setdefault("JWT_SECRET_KEY"' in line:
                assert False, (
                    f"test_experiment_api.py:{i+1}: "
                    "os.environ.setdefault('JWT_SECRET_KEY') は conftest.py で一元管理されています。"
                    "この行を削除してください。"
                )

    def test_conftest_provides_auth_headers_fixture(self):
        """conftest.pyがauth_headersフィクスチャを提供する"""
        conftest_path = Path(__file__).parent / "conftest.py"
        content = conftest_path.read_text()
        assert 'auth_headers' in content
        assert '@pytest.fixture' in content


class TestNoDuplicateEnvSettings:
    """テストファイル内の重複環境変数設定を検出しないことを確認"""

    def _check_no_duplicate_env_setdefault(self, test_file: Path) -> list[str]:
        """ファイル内の重複環境変数設定をチェック"""
        if not test_file.exists():
            return []

        content = test_file.read_text()
        lines = content.split('\n')
        violations = []

        # importセクション内でのみチェック
        in_import_section = True
        for i, line in enumerate(lines):
            if in_import_section:
                if line.startswith('def ') or line.startswith('class '):
                    in_import_section = False
                elif 'os.environ.setdefault("JWT_SECRET_KEY"' in line:
                    violations.append(f"{test_file.name}:{i+1}")

        return violations

    def test_no_duplicate_jwt_in_user_tests(self):
        """test_user.pyに重複JWT設定がない"""
        violations = self._check_no_duplicate_env_setdefault(
            Path(__file__).parent / "test_user.py"
        )
        assert len(violations) == 0, (
            f"重複するJWT設定が見つかりました: {violations}。"
            "conftest.pyで一元管理されているため削除してください。"
        )

    def test_no_duplicate_jwt_in_tenant_tests(self):
        """test_tenant.pyに重複JWT設定がない"""
        violations = self._check_no_duplicate_env_setdefault(
            Path(__file__).parent / "test_tenant.py"
        )
        assert len(violations) == 0, (
            f"重複するJWT設定が見つかりました: {violations}。"
            "conftest.pyで一元管理されているため削除してください。"
        )

    def test_no_duplicate_jwt_in_channels_tests(self):
        """test_channels.pyに重複JWT設定がない"""
        violations = self._check_no_duplicate_env_setdefault(
            Path(__file__).parent / "test_channels.py"
        )
        assert len(violations) == 0, (
            f"重複するJWT設定が見つかりました: {violations}。"
            "conftest.pyで一元管理されているため削除してください。"
        )
