"""P3-55: A/Bテスト基盤 - StatisticsService のテスト (TDD - GREEN phase)"""

import pytest
import math


# ---------------------------------------------------------------------------
# T-Test tests
# ---------------------------------------------------------------------------
class TestTTest:
    """t検定のテスト"""

    def test_t_test_significant_difference(self):
        """有意な差がある場合、統計的有意性を検出できる"""
        from app.services.statistics_service import StatisticsService

        service = StatisticsService()
        # 明らかに異なる2群（平均 3.0 vs 5.0）
        control = [2.0, 3.0, 4.0, 3.0, 3.0]
        treatment = [4.0, 5.0, 6.0, 5.0, 5.0]

        result = service.t_test(control, treatment)

        assert result["statistic"] is not None
        assert result["p_value"] is not None
        assert result["p_value"] < 0.05  # 統計的有意
        assert result["significant"] is True

    def test_t_test_no_significant_difference(self):
        """有意な差がない場合、統計的有意性はない"""
        from app.services.statistics_service import StatisticsService

        service = StatisticsService()
        # 類似した2群（分散が大きい）
        control = [1.0, 4.0, 7.0, 4.0, 4.0]
        treatment = [2.0, 5.0, 8.0, 5.0, 5.0]

        result = service.t_test(control, treatment)

        assert result["p_value"] > 0.05  # 統計的有意でない
        assert result["significant"] is False

    def test_t_test_returns_effect_size(self):
        """t検定の結果に効果量（Cohen's d）が含まれる"""
        from app.services.statistics_service import StatisticsService

        service = StatisticsService()
        control = [2.0, 3.0, 4.0, 3.0, 3.0]
        treatment = [4.0, 5.0, 6.0, 5.0, 5.0]

        result = service.t_test(control, treatment)

        assert "cohens_d" in result
        # Cohen's d は正の値（treatment > control）
        assert result["cohens_d"] > 0

    def test_t_test_insufficient_sample(self):
        """サンプルサイズが不足している場合は None を返す"""
        from app.services.statistics_service import StatisticsService

        service = StatisticsService()
        control = [3.0]  # 1件のみ
        treatment = [5.0]  # 1件のみ

        result = service.t_test(control, treatment)

        assert result["p_value"] is None
        assert result["statistic"] is None

    def test_t_test_empty_samples(self):
        """空のサンプルの場合は None を返す"""
        from app.services.statistics_service import StatisticsService

        service = StatisticsService()
        result = service.t_test([], [])

        assert result["p_value"] is None
        assert result["statistic"] is None


# ---------------------------------------------------------------------------
# Confidence Interval tests
# ---------------------------------------------------------------------------
class TestConfidenceInterval:
    """信頼区間のテスト"""

    def test_confidence_interval_95(self):
        """95%信頼区間を計算できる"""
        from app.services.statistics_service import StatisticsService

        service = StatisticsService()
        sample = [3.0, 4.0, 5.0, 4.0, 4.0]

        result = service.confidence_interval(sample, confidence=0.95)

        assert "lower" in result
        assert "upper" in result
        assert result["lower"] < result["upper"]
        # 平均 4.0 を含む
        assert result["lower"] < 4.0 < result["upper"]

    def test_confidence_interval_99(self):
        """99%信頼区間を計算できる"""
        from app.services.statistics_service import StatisticsService

        service = StatisticsService()
        sample = [3.0, 4.0, 5.0, 4.0, 4.0]

        ci_99 = service.confidence_interval(sample, confidence=0.99)

        # 信頼区間が計算されることを確認
        assert ci_99["lower"] is not None
        assert ci_99["upper"] is not None
        assert ci_99["lower"] < ci_99["upper"]

    def test_confidence_interval_single_sample(self):
        """サンプルが1件のみの場合は None を返す"""
        from app.services.statistics_service import StatisticsService

        service = StatisticsService()
        result = service.confidence_interval([3.0])

        assert result["lower"] is None
        assert result["upper"] is None

    def test_confidence_interval_empty_sample(self):
        """空のサンプルの場合は None を返す"""
        from app.services.statistics_service import StatisticsService

        service = StatisticsService()
        result = service.confidence_interval([])

        assert result["lower"] is None
        assert result["upper"] is None


# ---------------------------------------------------------------------------
# Cohen's d (Effect Size) tests
# ---------------------------------------------------------------------------
class TestCohensD:
    """効果量（Cohen's d）のテスト"""

    def test_cohens_d_large_effect(self):
        """大きな効果量を計算できる"""
        from app.services.statistics_service import StatisticsService

        service = StatisticsService()
        # 平均 3.0 vs 5.0（大きな差）
        control = [2.0, 3.0, 4.0, 3.0, 3.0]
        treatment = [4.0, 5.0, 6.0, 5.0, 5.0]

        d = service.cohens_d(control, treatment)

        # Cohen's d > 0.8 は大きな効果
        assert d > 0.8

    def test_cohens_d_medium_effect(self):
        """中程度の効果量を計算できる"""
        from app.services.statistics_service import StatisticsService

        service = StatisticsService()
        # 中程度の差
        control = [3.0, 4.0, 5.0, 4.0, 4.0]
        treatment = [4.0, 5.0, 6.0, 5.0, 5.0]

        d = service.cohens_d(control, treatment)

        # Cohen's d は 0.5〜0.8 の中程度の効果
        assert 0.5 <= d <= 1.5

    def test_cohens_d_negative(self):
        """control > treatment の場合は負の値"""
        from app.services.statistics_service import StatisticsService

        service = StatisticsService()
        control = [4.0, 5.0, 6.0, 5.0, 5.0]
        treatment = [2.0, 3.0, 4.0, 3.0, 3.0]

        d = service.cohens_d(control, treatment)

        assert d < 0

    def test_cohens_d_zero(self):
        """同じ平均の場合は0に近い"""
        from app.services.statistics_service import StatisticsService

        service = StatisticsService()
        control = [3.0, 4.0, 5.0, 4.0, 4.0]
        treatment = [3.0, 4.0, 5.0, 4.0, 4.0]

        d = service.cohens_d(control, treatment)

        assert abs(d) < 0.01


# ---------------------------------------------------------------------------
# Experiment Result Analysis tests
# ---------------------------------------------------------------------------
class TestExperimentResultAnalysis:
    """実験結果分析のテスト"""

    def test_analyze_experiment_results(self):
        """実験結果を分析できる"""
        from app.services.statistics_service import StatisticsService

        service = StatisticsService()
        # Control: 平均 3.0
        control_metrics = [2.0, 3.0, 4.0, 3.0, 3.0]
        # Treatment: 平均 5.0
        treatment_metrics = [4.0, 5.0, 6.0, 5.0, 5.0]

        result = service.analyze_experiment(
            control_metrics=control_metrics,
            treatment_metrics=treatment_metrics,
        )

        assert "control" in result
        assert "treatment" in result
        assert "comparison" in result

        # 各バリアントの統計
        assert result["control"]["mean"] == pytest.approx(3.0)
        assert result["treatment"]["mean"] == pytest.approx(5.0)

        # 比較結果
        assert result["comparison"]["significant"] is True
        assert result["comparison"]["winner"] == "treatment"

    def test_analyze_experiment_with_ci(self):
        """実験結果に信頼区間が含まれる"""
        from app.services.statistics_service import StatisticsService

        service = StatisticsService()
        control_metrics = [3.0, 4.0, 5.0, 4.0, 4.0]
        treatment_metrics = [4.0, 5.0, 6.0, 5.0, 5.0]

        result = service.analyze_experiment(
            control_metrics=control_metrics,
            treatment_metrics=treatment_metrics,
        )

        assert "ci_lower" in result["control"]
        assert "ci_upper" in result["control"]
        assert "ci_lower" in result["treatment"]
        assert "ci_upper" in result["treatment"]

    def test_analyze_experiment_no_winner(self):
        """有意な差がない場合は winner なし"""
        from app.services.statistics_service import StatisticsService

        service = StatisticsService()
        # 分散が大きく、差が有意でないケース
        control_metrics = [1.0, 4.0, 7.0, 4.0, 4.0]
        treatment_metrics = [2.0, 5.0, 8.0, 5.0, 5.0]

        result = service.analyze_experiment(
            control_metrics=control_metrics,
            treatment_metrics=treatment_metrics,
        )

        assert result["comparison"]["significant"] is False
        assert result["comparison"]["winner"] is None
