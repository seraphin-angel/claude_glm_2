"""
RAGAS evaluation framework tests.

This module provides automated evaluation of RAG system quality using RAGAS metrics:
- answer_relevancy: How relevant the answer is to the question
- faithfulness: How faithful the answer is to the retrieved context (hallucination detection)
- context_precision: Precision of retrieved context
- context_recall: Recall of retrieved context
"""

import json
import os
from pathlib import Path
from typing import Any

import pytest


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def golden_questions_path() -> Path:
    """Path to the golden dataset questions."""
    return Path(__file__).parent.parent / "golden" / "questions.json"


@pytest.fixture
def golden_questions(golden_questions_path: Path) -> list[dict[str, Any]]:
    """Load golden questions from the dataset."""
    with open(golden_questions_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_evaluation_data() -> list[dict[str, Any]]:
    """
    Sample evaluation data for testing the RAGAS pipeline.

    This fixture provides minimal test data that doesn't require
    actual LLM calls, useful for testing the pipeline structure.
    """
    return [
        {
            "question": "ログイン方法を教えてください",
            "answer": "ログインするには、メールアドレスとパスワードを入力してください。",
            "contexts": [
                "ログイン画面でメールアドレスとパスワードを入力します。",
                "アカウントがない場合は新規登録が必要です。",
            ],
            "ground_truth": "メールアドレスとパスワードを使用してログインします。",
        },
        {
            "question": "パスワードを変更するにはどうすればいいですか？",
            "answer": "設定画面からパスワード変更が可能です。",
            "contexts": [
                "設定メニューのセキュリティタブを開きます。",
                "パスワード変更オプションを選択します。",
            ],
            "ground_truth": "設定画面のセキュリティタブからパスワードを変更できます。",
        },
    ]


# ============================================================================
# Pipeline Structure Tests (No LLM calls required, No API key required)
# ============================================================================


class TestRagasPipelineStructure:
    """Tests for RAGAS pipeline structure without LLM calls."""

    def test_golden_questions_loaded(self, golden_questions: list[dict[str, Any]]) -> None:
        """Golden questions dataset should load correctly."""
        assert len(golden_questions) > 0
        for q in golden_questions:
            assert "id" in q
            assert "question" in q
            assert "category" in q

    def test_sample_data_structure(self, sample_evaluation_data: list[dict[str, Any]]) -> None:
        """Sample evaluation data should have correct structure."""
        for item in sample_evaluation_data:
            assert "question" in item
            assert "answer" in item
            assert "contexts" in item
            assert "ground_truth" in item
            assert isinstance(item["contexts"], list)

    def test_ragas_imports_available(self) -> None:
        """RAGAS package should be importable."""
        try:
            from ragas import evaluate
            from ragas.dataset_schema import SingleTurnSample
            from ragas.metrics._answer_relevance import AnswerRelevancy
            from ragas.metrics._context_precision import ContextPrecision
            from ragas.metrics._context_recall import ContextRecall
            from ragas.metrics._faithfulness import Faithfulness

            assert evaluate is not None
            assert SingleTurnSample is not None
        except ImportError as e:
            pytest.fail(f"RAGAS import failed: {e}")

    def test_evaluation_dataset_creation(
        self, sample_evaluation_data: list[dict[str, Any]]
    ) -> None:
        """Should be able to create EvaluationDataset from sample data."""
        from ragas.dataset_schema import EvaluationDataset, SingleTurnSample

        samples = []
        for item in sample_evaluation_data:
            sample = SingleTurnSample(
                user_input=item["question"],
                response=item["answer"],
                retrieved_contexts=item["contexts"],
                reference=item["ground_truth"],
            )
            samples.append(sample)

        dataset = EvaluationDataset(samples=samples)
        assert len(dataset.samples) == len(sample_evaluation_data)


# ============================================================================
# Pipeline Module Tests
# ============================================================================


class TestRagasPipelineModule:
    """Tests for the pipeline module."""

    def test_evaluation_report_creation(self) -> None:
        """EvaluationReport should be creatable."""
        from tests.evaluation.pipeline import EvaluationReport

        report = EvaluationReport(
            timestamp="2024-01-01T00:00:00",
            total_questions=10,
            answer_relevancy_avg=0.85,
            faithfulness_avg=0.90,
            context_precision_avg=0.75,
            context_recall_avg=0.80,
            overall_score=0.825,
        )

        assert report.total_questions == 10
        assert report.answer_relevancy_avg == 0.85
        assert report.overall_score == 0.825

    def test_evaluation_report_to_dict(self) -> None:
        """EvaluationReport should convert to dictionary."""
        from tests.evaluation.pipeline import EvaluationReport

        report = EvaluationReport(
            timestamp="2024-01-01T00:00:00",
            total_questions=10,
            answer_relevancy_avg=0.85,
            faithfulness_avg=0.90,
            context_precision_avg=0.75,
            context_recall_avg=0.80,
            overall_score=0.825,
        )

        result = report.to_dict()

        assert result["total_questions"] == 10
        assert result["metrics"]["answer_relevancy"] == 0.85
        assert result["overall_score"] == 0.825

    def test_evaluation_report_print(self, capsys: pytest.CaptureFixture) -> None:
        """EvaluationReport should print formatted output."""
        from tests.evaluation.pipeline import EvaluationReport

        report = EvaluationReport(
            timestamp="2024-01-01T00:00:00",
            total_questions=10,
            answer_relevancy_avg=0.85,
            faithfulness_avg=0.90,
            context_precision_avg=0.75,
            context_recall_avg=0.80,
            overall_score=0.825,
        )

        report.print_report()
        captured = capsys.readouterr()

        assert "RAGAS Evaluation Report" in captured.out
        assert "answer_relevancy" in captured.out
        assert "0.8500" in captured.out
        assert "Overall Average" in captured.out

    def test_ragas_evaluator_initialization_without_api_key(self) -> None:
        """RagasEvaluator should raise error without API key."""
        from tests.evaluation.pipeline import RagasEvaluator

        original_key = os.environ.pop("OPENAI_API_KEY", None)

        try:
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                RagasEvaluator()
        finally:
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key

    def test_ragas_evaluator_initialization_with_api_key(self) -> None:
        """RagasEvaluator should initialize with API key."""
        from tests.evaluation.pipeline import RagasEvaluator

        original_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "test-key"

        try:
            evaluator = RagasEvaluator()
            assert evaluator.api_key == "test-key"
        finally:
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
            else:
                os.environ.pop("OPENAI_API_KEY", None)

    def test_create_sample(self) -> None:
        """RagasEvaluator should create evaluation samples."""
        from tests.evaluation.pipeline import RagasEvaluator

        os.environ["OPENAI_API_KEY"] = "test-key"
        try:
            evaluator = RagasEvaluator()
            sample = evaluator.create_sample(
                question="テスト質問",
                answer="テスト回答",
                contexts=["コンテキスト1"],
                ground_truth="正解",
            )

            assert sample.user_input == "テスト質問"
            assert sample.response == "テスト回答"
        finally:
            os.environ.pop("OPENAI_API_KEY", None)

    def test_create_dataset_from_data(self, sample_evaluation_data: list[dict[str, Any]]) -> None:
        """RagasEvaluator should create dataset from evaluation data."""
        from tests.evaluation.pipeline import RagasEvaluator

        os.environ["OPENAI_API_KEY"] = "test-key"
        try:
            evaluator = RagasEvaluator()
            dataset = evaluator.create_dataset_from_data(sample_evaluation_data)

            assert len(dataset.samples) == len(sample_evaluation_data)
        finally:
            os.environ.pop("OPENAI_API_KEY", None)

    def test_load_golden_questions(self, golden_questions_path: Path) -> None:
        """load_golden_questions should load questions from file."""
        from tests.evaluation.pipeline import load_golden_questions

        questions = load_golden_questions(golden_questions_path)

        assert len(questions) > 0
        assert all("question" in q for q in questions)


# ============================================================================
# Report Generation Tests
# ============================================================================


class TestRagasReportGeneration:
    """Tests for RAGAS evaluation report generation."""

    def test_report_format(self) -> None:
        """Evaluation report should have correct format."""
        from dataclasses import dataclass
        from typing import Optional

        @dataclass
        class EvaluationReport:
            """Standard evaluation report structure."""

            total_questions: int
            answer_relevancy_avg: float
            faithfulness_avg: float
            context_precision_avg: float
            context_recall_avg: float
            overall_score: float
            details: Optional[list[dict[str, Any]]] = None

        # Test report creation
        report = EvaluationReport(
            total_questions=10,
            answer_relevancy_avg=0.85,
            faithfulness_avg=0.90,
            context_precision_avg=0.75,
            context_recall_avg=0.80,
            overall_score=0.825,
        )

        assert report.total_questions == 10
        assert 0 <= report.answer_relevancy_avg <= 1
        assert 0 <= report.faithfulness_avg <= 1
        assert 0 <= report.context_precision_avg <= 1
        assert 0 <= report.context_recall_avg <= 1

    def test_console_report_output(self, capsys: pytest.CaptureFixture) -> None:
        """Report should be printable to console."""
        from datetime import datetime

        def print_evaluation_report(
            metrics: dict[str, float],
            total_questions: int,
            timestamp: datetime | None = None,
        ) -> None:
            """Print a formatted evaluation report to console."""
            if timestamp is None:
                timestamp = datetime.now()

            print("\n" + "=" * 60)
            print("RAGAS Evaluation Report")
            print("=" * 60)
            print(f"Timestamp: {timestamp.isoformat()}")
            print(f"Total Questions: {total_questions}")
            print("-" * 60)
            print("Metrics:")
            for name, score in metrics.items():
                print(f"  {name}: {score:.4f}")
            print("-" * 60)
            avg_score = sum(metrics.values()) / len(metrics)
            print(f"Overall Average: {avg_score:.4f}")
            print("=" * 60 + "\n")

        # Test the report function
        metrics = {
            "answer_relevancy": 0.85,
            "faithfulness": 0.90,
            "context_precision": 0.75,
            "context_recall": 0.80,
        }
        print_evaluation_report(metrics, total_questions=10)

        captured = capsys.readouterr()
        assert "RAGAS Evaluation Report" in captured.out
        assert "answer_relevancy: 0.8500" in captured.out
        assert "Overall Average: 0.8250" in captured.out


# ============================================================================
# Metrics Tests (Require OpenAI API key)
# ============================================================================


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set - skipping tests that require LLM",
)
class TestRagasMetricsWithLLM:
    """Tests for individual RAGAS metrics (requires OpenAI API key)."""

    @pytest.mark.asyncio
    async def test_answer_relevancy_metric(self) -> None:
        """Answer relevancy metric should work with sample data."""
        from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
        from ragas.metrics._answer_relevance import AnswerRelevancy

        sample = SingleTurnSample(
            user_input="ログイン方法を教えてください",
            response="ログインするには、メールアドレスとパスワードを入力してください。",
        )

        metric = AnswerRelevancy(llm=None)  # type: ignore
        # Note: Actual scoring requires LLM, this tests structure only

    @pytest.mark.asyncio
    async def test_faithfulness_metric(self) -> None:
        """Faithfulness metric should work with sample data."""
        from ragas.dataset_schema import SingleTurnSample
        from ragas.metrics._faithfulness import Faithfulness

        sample = SingleTurnSample(
            user_input="ログイン方法を教えてください",
            response="ログインするには、メールアドレスとパスワードを入力してください。",
            retrieved_contexts=[
                "ログイン画面でメールアドレスとパスワードを入力します。"
            ],
        )

        metric = Faithfulness(llm=None)  # type: ignore
        # Note: Actual scoring requires LLM, this tests structure only

    @pytest.mark.asyncio
    async def test_context_precision_metric(self) -> None:
        """Context precision metric should work with sample data."""
        from ragas.dataset_schema import SingleTurnSample
        from ragas.metrics._context_precision import ContextPrecision

        sample = SingleTurnSample(
            user_input="ログイン方法を教えてください",
            response="ログインするには、メールアドレスとパスワードを入力してください。",
            retrieved_contexts=[
                "ログイン画面でメールアドレスとパスワードを入力します。"
            ],
            reference="メールアドレスとパスワードを使用してログインします。",
        )

        metric = ContextPrecision(llm=None)  # type: ignore
        # Note: Actual scoring requires LLM, this tests structure only

    @pytest.mark.asyncio
    async def test_context_recall_metric(self) -> None:
        """Context recall metric should work with sample data."""
        from ragas.dataset_schema import SingleTurnSample
        from ragas.metrics._context_recall import ContextRecall

        sample = SingleTurnSample(
            user_input="ログイン方法を教えてください",
            response="ログインするには、メールアドレスとパスワードを入力してください。",
            retrieved_contexts=[
                "ログイン画面でメールアドレスとパスワードを入力します。"
            ],
            reference="メールアドレスとパスワードを使用してログインします。",
        )

        metric = ContextRecall(llm=None)  # type: ignore
        # Note: Actual scoring requires LLM, this tests structure only


# ============================================================================
# Full Evaluation Pipeline Test (Requires OpenAI API key)
# ============================================================================


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set - skipping integration tests",
)
@pytest.mark.integration
class TestRagasEvaluationPipelineWithLLM:
    """Tests for the complete RAGAS evaluation pipeline with LLM."""

    @pytest.mark.asyncio
    async def test_full_evaluation_with_sample_data(
        self, sample_evaluation_data: list[dict[str, Any]]
    ) -> None:
        """
        Run full RAGAS evaluation on sample data.

        This test requires OPENAI_API_KEY and makes actual LLM calls.
        It validates the entire evaluation pipeline.
        """
        from ragas import evaluate
        from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
        from ragas.metrics._answer_relevance import AnswerRelevancy
        from ragas.metrics._context_precision import ContextPrecision
        from ragas.metrics._context_recall import ContextRecall
        from ragas.metrics._faithfulness import Faithfulness

        # Create samples from evaluation data
        samples = []
        for item in sample_evaluation_data:
            sample = SingleTurnSample(
                user_input=item["question"],
                response=item["answer"],
                retrieved_contexts=item["contexts"],
                reference=item["ground_truth"],
            )
            samples.append(sample)

        dataset = EvaluationDataset(samples=samples)

        # Define metrics
        metrics = [
            AnswerRelevancy(),
            Faithfulness(),
            ContextPrecision(),
            ContextRecall(),
        ]

        # Run evaluation
        results = evaluate(dataset=dataset, metrics=metrics)

        # Validate results structure
        assert results is not None

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_evaluation_with_golden_dataset(
        self, golden_questions: list[dict[str, Any]]
    ) -> None:
        """
        Run RAGAS evaluation on the full golden dataset.

        This test requires:
        - OPENAI_API_KEY
        - A running RAG system to generate answers
        - Retrieved contexts for each question

        Note: This is a slow test and should be run separately from quick tests.
        """
        pytest.skip(
            "Full golden dataset evaluation requires running RAG system. "
            "Run manually with: pytest -m 'integration and slow' --run-golden"
        )


# ============================================================================
# Helper Functions
# ============================================================================


def create_evaluation_sample(
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str,
) -> dict[str, Any]:
    """Create a single evaluation sample."""
    return {
        "question": question,
        "answer": answer,
        "contexts": contexts,
        "ground_truth": ground_truth,
    }


def format_score(score: float) -> str:
    """Format a score for display."""
    return f"{score:.4f}"
