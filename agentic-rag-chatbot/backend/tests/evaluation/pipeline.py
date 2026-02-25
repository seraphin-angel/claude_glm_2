"""
RAGAS Evaluation Pipeline for RAG System.

This module provides a complete evaluation pipeline using RAGAS metrics:
- answer_relevancy: How relevant the answer is to the question
- faithfulness: How faithful the answer is to the retrieved context
- context_precision: Precision of retrieved context
- context_recall: Recall of retrieved context
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ragas import evaluate
from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
from ragas.metrics._answer_relevance import AnswerRelevancy
from ragas.metrics._context_precision import ContextPrecision
from ragas.metrics._context_recall import ContextRecall
from ragas.metrics._faithfulness import Faithfulness


@dataclass
class EvaluationReport:
    """Standard evaluation report structure."""

    timestamp: str
    total_questions: int
    answer_relevancy_avg: float
    faithfulness_avg: float
    context_precision_avg: float
    context_recall_avg: float
    overall_score: float
    details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "timestamp": self.timestamp,
            "total_questions": self.total_questions,
            "metrics": {
                "answer_relevancy": self.answer_relevancy_avg,
                "faithfulness": self.faithfulness_avg,
                "context_precision": self.context_precision_avg,
                "context_recall": self.context_recall_avg,
            },
            "overall_score": self.overall_score,
            "details": self.details,
        }

    def print_report(self) -> None:
        """Print a formatted evaluation report to console."""
        print("\n" + "=" * 60)
        print("RAGAS Evaluation Report")
        print("=" * 60)
        print(f"Timestamp: {self.timestamp}")
        print(f"Total Questions: {self.total_questions}")
        print("-" * 60)
        print("Metrics:")
        print(f"  answer_relevancy:   {self.answer_relevancy_avg:.4f}")
        print(f"  faithfulness:       {self.faithfulness_avg:.4f}")
        print(f"  context_precision:  {self.context_precision_avg:.4f}")
        print(f"  context_recall:     {self.context_recall_avg:.4f}")
        print("-" * 60)
        print(f"Overall Average: {self.overall_score:.4f}")
        print("=" * 60 + "\n")


class RagasEvaluator:
    """RAGAS evaluation pipeline for RAG systems."""

    def __init__(
        self,
        openai_api_key: str | None = None,
        model: str = "gpt-4o-mini",
    ) -> None:
        """
        Initialize the RAGAS evaluator.

        Args:
            openai_api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI model to use for evaluation
        """
        self.api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable "
                "or pass openai_api_key parameter."
            )

        self.model = model

        # Initialize metrics
        self.metrics = [
            AnswerRelevancy(),
            Faithfulness(),
            ContextPrecision(),
            ContextRecall(),
        ]

    def create_sample(
        self,
        question: str,
        answer: str,
        contexts: list[str],
        ground_truth: str,
    ) -> SingleTurnSample:
        """
        Create a single evaluation sample.

        Args:
            question: The user's question
            answer: The generated answer
            contexts: Retrieved context passages
            ground_truth: The expected/reference answer

        Returns:
            SingleTurnSample for RAGAS evaluation
        """
        return SingleTurnSample(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts,
            reference=ground_truth,
        )

    def create_dataset_from_data(
        self,
        evaluation_data: list[dict[str, Any]],
    ) -> EvaluationDataset:
        """
        Create an EvaluationDataset from a list of evaluation data.

        Args:
            evaluation_data: List of dicts with question, answer, contexts, ground_truth

        Returns:
            EvaluationDataset ready for RAGAS evaluation
        """
        samples = []
        for item in evaluation_data:
            sample = self.create_sample(
                question=item["question"],
                answer=item["answer"],
                contexts=item.get("contexts", []),
                ground_truth=item.get("ground_truth", ""),
            )
            samples.append(sample)

        return EvaluationDataset(samples=samples)

    async def evaluate_async(
        self,
        evaluation_data: list[dict[str, Any]],
    ) -> EvaluationReport:
        """
        Run RAGAS evaluation asynchronously.

        Args:
            evaluation_data: List of dicts with question, answer, contexts, ground_truth

        Returns:
            EvaluationReport with all metric scores
        """
        dataset = self.create_dataset_from_data(evaluation_data)

        # Run evaluation
        results = evaluate(dataset=dataset, metrics=self.metrics)

        # Extract scores
        # RAGAS returns results as a pandas DataFrame-like object
        scores = self._extract_scores(results)

        return EvaluationReport(
            timestamp=datetime.now().isoformat(),
            total_questions=len(evaluation_data),
            answer_relevancy_avg=scores.get("answer_relevancy", 0.0),
            faithfulness_avg=scores.get("faithfulness", 0.0),
            context_precision_avg=scores.get("context_precision", 0.0),
            context_recall_avg=scores.get("context_recall", 0.0),
            overall_score=scores.get("overall", 0.0),
            details=scores.get("details", []),
        )

    def evaluate(
        self,
        evaluation_data: list[dict[str, Any]],
    ) -> EvaluationReport:
        """
        Run RAGAS evaluation synchronously.

        Args:
            evaluation_data: List of dicts with question, answer, contexts, ground_truth

        Returns:
            EvaluationReport with all metric scores
        """
        return asyncio.run(self.evaluate_async(evaluation_data))

    def _extract_scores(self, results: Any) -> dict[str, Any]:
        """
        Extract scores from RAGAS evaluation results.

        Args:
            results: RAGAS evaluation results

        Returns:
            Dictionary with extracted scores
        """
        scores: dict[str, Any] = {
            "answer_relevancy": 0.0,
            "faithfulness": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
            "overall": 0.0,
            "details": [],
        }

        try:
            # Try to convert results to pandas if available
            import pandas as pd

            if hasattr(results, "to_pandas"):
                df = results.to_pandas()
            elif isinstance(results, pd.DataFrame):
                df = results
            else:
                # Try direct attribute access
                return self._extract_scores_from_attributes(results)

            # Calculate averages for each metric
            metric_columns = [
                "answer_relevancy",
                "faithfulness",
                "context_precision",
                "context_recall",
            ]

            valid_scores = []
            for col in metric_columns:
                if col in df.columns:
                    avg = df[col].mean()
                    if not pd.isna(avg):
                        scores[col] = float(avg)
                        valid_scores.append(float(avg))

            # Calculate overall average
            if valid_scores:
                scores["overall"] = sum(valid_scores) / len(valid_scores)

            # Extract details if available
            scores["details"] = df.to_dict(orient="records") if len(df) > 0 else []

        except ImportError:
            # Fallback if pandas is not available
            return self._extract_scores_from_attributes(results)
        except Exception:
            # If any error occurs, return default scores
            pass

        return scores

    def _extract_scores_from_attributes(self, results: Any) -> dict[str, Any]:
        """Fallback method to extract scores from result attributes."""
        scores: dict[str, Any] = {
            "answer_relevancy": 0.0,
            "faithfulness": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
            "overall": 0.0,
            "details": [],
        }

        valid_scores = []
        for metric in ["answer_relevancy", "faithfulness", "context_precision", "context_recall"]:
            if hasattr(results, metric):
                value = getattr(results, metric)
                if isinstance(value, (int, float)):
                    scores[metric] = float(value)
                    valid_scores.append(float(value))

        if valid_scores:
            scores["overall"] = sum(valid_scores) / len(valid_scores)

        return scores


def load_golden_questions(path: Path | str) -> list[dict[str, Any]]:
    """
    Load golden questions from JSON file.

    Args:
        path: Path to the golden questions JSON file

    Returns:
        List of golden question dictionaries
    """
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_evaluation_from_file(
    questions_path: Path | str,
    rag_system: Any = None,
    print_report: bool = True,
) -> EvaluationReport:
    """
    Run RAGAS evaluation using questions from a file.

    This is a convenience function that loads questions and runs evaluation.

    Args:
        questions_path: Path to questions JSON file
        rag_system: Optional RAG system to generate answers
        print_report: Whether to print the report to console

    Returns:
        EvaluationReport with all metric scores
    """
    questions = load_golden_questions(questions_path)

    # If RAG system is provided, generate answers and contexts
    if rag_system is not None:
        evaluation_data = []
        for q in questions:
            result = rag_system.query(q["question"])
            evaluation_data.append({
                "question": q["question"],
                "answer": result.get("answer", ""),
                "contexts": result.get("contexts", []),
                "ground_truth": q.get("expected_keywords", [""])[0] if q.get("expected_keywords") else "",
            })
    else:
        # Use questions as-is (requires pre-generated answers)
        evaluation_data = questions

    evaluator = RagasEvaluator()
    report = evaluator.evaluate(evaluation_data)

    if print_report:
        report.print_report()

    return report


def main() -> None:
    """Main entry point for CLI evaluation."""
    import argparse

    parser = argparse.ArgumentParser(description="Run RAGAS evaluation on RAG system")
    parser.add_argument(
        "--questions",
        type=str,
        default="tests/golden/questions.json",
        help="Path to questions JSON file",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to save evaluation report as JSON",
    )
    parser.add_argument(
        "--no-print",
        action="store_true",
        help="Don't print report to console",
    )

    args = parser.parse_args()

    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is required")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        return

    # Run evaluation
    try:
        questions = load_golden_questions(args.questions)
        print(f"Loaded {len(questions)} questions from {args.questions}")

        # Note: This requires answers and contexts to be pre-generated
        # In production, you would integrate with the RAG system here
        print("\nNote: This requires pre-generated answers and contexts.")
        print("For full evaluation, use the evaluator with RAG system integration.")

        if args.output:
            # Create a placeholder report
            report = EvaluationReport(
                timestamp=datetime.now().isoformat(),
                total_questions=len(questions),
                answer_relevancy_avg=0.0,
                faithfulness_avg=0.0,
                context_precision_avg=0.0,
                context_recall_avg=0.0,
                overall_score=0.0,
            )
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
            print(f"\nReport saved to {args.output}")

    except FileNotFoundError:
        print(f"Error: Questions file not found: {args.questions}")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in questions file: {e}")
    except Exception as e:
        print(f"Error during evaluation: {e}")


if __name__ == "__main__":
    main()
