"""循環インポートがないことを確認するテスト

TDD Red-Green-Refactor:
1. RED: このテストは現在循環インポートのため失敗する
2. GREEN: chat_service.py で遅延importを使用して修正
3. REFACTOR: 必要に応じて整理

Note: 循環インポートはPythonのimport順序に依存するため、
サブプロセスで個別にテストすることが最も確実です。
"""

import subprocess
import sys

import pytest


class TestNoCircularImports:
    """循環インポートがないことを確認するテストクラス"""

    def test_no_circular_imports_critical_modules(self):
        """Critical: 主要モジュールが循環インポートなしでimportできること

        循環インポートチェーン（修正前）:
        app.agents.agent
          -> app.agents.tools
          -> app.agents.tools.escalation
          -> app.services.escalation_service
          -> app.services.__init__
          -> app.services.chat_service
          -> app.agents.agent (循環!)

        修正方針:
        chat_service.py のトップレベルimportを遅延importに変更
        """
        # 以下のimportが成功すれば循環インポートなし
        from app.agents.agent import build_agent, get_agent, reset_agent
        from app.services.chat_service import ChatService, get_chat_service
        from app.services.escalation_service import EscalationService

        # 基本的な検証
        assert callable(build_agent)
        assert callable(get_agent)
        assert callable(reset_agent)
        assert ChatService is not None
        assert callable(get_chat_service)
        assert EscalationService is not None

    def test_all_tools_can_be_imported(self):
        """toolsモジュールが正常にimportできること"""
        from app.agents.tools import (
            analyze_image,
            ask_human,
            check_input_safety,
            check_output_safety,
            check_quality,
            check_relevance,
            classify_query,
            escalate_to_human,
            generate_answer,
            rewrite_query,
            search_knowledge,
        )

        # 全てのツールが存在することを確認（StructuredToolはcallableではないのでNoneチェック）
        tools = [
            analyze_image,
            ask_human,
            check_input_safety,
            check_output_safety,
            check_quality,
            check_relevance,
            classify_query,
            escalate_to_human,
            generate_answer,
            rewrite_query,
            search_knowledge,
        ]
        for tool in tools:
            assert tool is not None

    def test_all_services_can_be_imported(self):
        """servicesモジュールが正常にimportできること"""
        from app.services import ChatService, get_chat_service

        assert ChatService is not None
        assert callable(get_chat_service)

    def test_import_order_independence(self):
        """import順序に依存しないことを確認

        異なる順序でimportしてもエラーが発生しないことを確認
        """
        # パターン1: services -> agents
        from app.services.chat_service import ChatService
        from app.agents.agent import get_agent

        assert ChatService is not None
        assert callable(get_agent)

    def test_escalation_tool_imports_escalation_service(self):
        """escalationツールがescalation_serviceを正常にimportできること"""
        from app.agents.tools.escalation import escalate_to_human
        from app.services.escalation_service import EscalationService

        # StructuredToolはcallableではないのでNoneチェック
        assert escalate_to_human is not None
        assert EscalationService is not None

    def test_agent_import_in_fresh_process(self):
        """Critical: 新しいPythonプロセスでagentをimportできること

        循環インポートはimport順序に依存するため、
        新しいプロセスでテストすることが最も確実です。
        """
        code = """
import sys
sys.path.insert(0, '/workspace/agentic-rag-chatbot/backend')
from app.agents.agent import build_agent, get_agent, reset_agent
print('SUCCESS')
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Import failed: {result.stderr}"
        assert "SUCCESS" in result.stdout

    def test_chat_service_import_in_fresh_process(self):
        """Critical: 新しいPythonプロセスでchat_serviceをimportできること"""
        code = """
import sys
sys.path.insert(0, '/workspace/agentic-rag-chatbot/backend')
from app.services.chat_service import ChatService, get_chat_service
print('SUCCESS')
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Import failed: {result.stderr}"
        assert "SUCCESS" in result.stdout

    def test_escalation_import_in_fresh_process(self):
        """Critical: 新しいPythonプロセスでescalation関連をimportできること"""
        code = """
import sys
sys.path.insert(0, '/workspace/agentic-rag-chatbot/backend')
from app.agents.tools.escalation import escalate_to_human
from app.services.escalation_service import EscalationService
print('SUCCESS')
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Import failed: {result.stderr}"
        assert "SUCCESS" in result.stdout

    def test_full_import_chain_in_fresh_process(self):
        """Critical: 新しいPythonプロセスで全モジュールを順番にimportできること

        これが最も確実な循環インポートテストです。
        """
        code = """
import sys
sys.path.insert(0, '/workspace/agentic-rag-chatbot/backend')

# 循環インポートチェーンを意識した順序でimport
from app.agents.tools.escalation import escalate_to_human
from app.services.escalation_service import EscalationService
from app.services.chat_service import ChatService
from app.agents.agent import build_agent, get_agent

print('SUCCESS')
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Import failed: {result.stderr}"
        assert "SUCCESS" in result.stdout
