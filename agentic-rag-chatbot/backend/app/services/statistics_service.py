"""P3-55: A/Bテスト基盤 - 統計分析サービス"""

import math
import statistics
from typing import Optional


class StatisticsService:
    """統計分析サービス（t検定、信頼区間、効果量）"""

    def t_test(
        self,
        control: list[float],
        treatment: list[float],
    ) -> dict:
        """スチューデントのt検定（ウェルチのt検定）を実行する。

        Args:
            control: 対照群のデータ
            treatment: 処置群のデータ

        Returns:
            検定結果（statistic, p_value, significant, cohens_d）
        """
        if len(control) < 2 or len(treatment) < 2:
            return {
                "statistic": None,
                "p_value": None,
                "significant": False,
                "cohens_d": None,
            }

        # 各群の平均と分散
        mean_c = statistics.mean(control)
        mean_t = statistics.mean(treatment)
        var_c = statistics.variance(control)
        var_t = statistics.variance(treatment)
        n_c = len(control)
        n_t = len(treatment)

        # ウェルチのt検定
        se = math.sqrt(var_c / n_c + var_t / n_t)
        if se == 0:
            return {
                "statistic": 0.0,
                "p_value": 1.0,
                "significant": False,
                "cohens_d": 0.0,
            }

        t_stat = (mean_t - mean_c) / se

        # 自由度（ウェルチ・サタスウェイトの式）
        df_num = (var_c / n_c + var_t / n_t) ** 2
        df_denom = (var_c / n_c) ** 2 / (n_c - 1) + (var_t / n_t) ** 2 / (n_t - 1)
        df = df_num / df_denom if df_denom > 0 else 1

        # p値（両側検定）
        p_value = self._t_distribution_pvalue(abs(t_stat), df)

        # Cohen's d
        d = self.cohens_d(control, treatment)

        return {
            "statistic": t_stat,
            "p_value": p_value,
            "significant": p_value < 0.05,
            "cohens_d": d,
        }

    def confidence_interval(
        self,
        sample: list[float],
        confidence: float = 0.95,
    ) -> dict:
        """信頼区間を計算する。

        Args:
            sample: サンプルデータ
            confidence: 信頼係数（デフォルト 0.95）

        Returns:
            信頼区間（lower, upper）
        """
        if len(sample) < 2:
            return {"lower": None, "upper": None}

        n = len(sample)
        mean = statistics.mean(sample)
        se = statistics.stdev(sample) / math.sqrt(n)

        # t値（両側）
        alpha = 1 - confidence
        df = n - 1
        t_crit = self._t_critical_value(alpha / 2, df)

        margin = t_crit * se

        return {
            "lower": mean - margin,
            "upper": mean + margin,
        }

    def cohens_d(
        self,
        control: list[float],
        treatment: list[float],
    ) -> float:
        """Cohen's d（効果量）を計算する。

        Args:
            control: 対照群のデータ
            treatment: 処置群のデータ

        Returns:
            効果量（正の値は treatment > control を示す）
        """
        if len(control) < 2 or len(treatment) < 2:
            return 0.0

        mean_c = statistics.mean(control)
        mean_t = statistics.mean(treatment)
        var_c = statistics.variance(control)
        var_t = statistics.variance(treatment)
        n_c = len(control)
        n_t = len(treatment)

        # プールド標準偏差
        pooled_std = math.sqrt(((n_c - 1) * var_c + (n_t - 1) * var_t) / (n_c + n_t - 2))

        if pooled_std == 0:
            return 0.0

        return (mean_t - mean_c) / pooled_std

    def analyze_experiment(
        self,
        control_metrics: list[float],
        treatment_metrics: list[float],
    ) -> dict:
        """実験結果を分析する。

        Args:
            control_metrics: 対照群の指標
            treatment_metrics: 処置群の指標

        Returns:
            分析結果（各バリアントの統計、比較結果）
        """
        # 各バリアントの統計
        control_stats = self._compute_stats(control_metrics)
        treatment_stats = self._compute_stats(treatment_metrics)

        # 信頼区間
        control_ci = self.confidence_interval(control_metrics)
        treatment_ci = self.confidence_interval(treatment_metrics)

        # t検定
        comparison = self.t_test(control_metrics, treatment_metrics)

        # 勝者判定
        winner = None
        if comparison["significant"]:
            if control_stats["mean"] > treatment_stats["mean"]:
                winner = "control"
            else:
                winner = "treatment"

        return {
            "control": {
                **control_stats,
                "ci_lower": control_ci["lower"],
                "ci_upper": control_ci["upper"],
            },
            "treatment": {
                **treatment_stats,
                "ci_lower": treatment_ci["lower"],
                "ci_upper": treatment_ci["upper"],
            },
            "comparison": {
                "statistic": comparison["statistic"],
                "p_value": comparison["p_value"],
                "significant": comparison["significant"],
                "cohens_d": comparison["cohens_d"],
                "winner": winner,
            },
        }

    def _compute_stats(self, sample: list[float]) -> dict:
        """サンプルの基本統計量を計算する。"""
        if not sample:
            return {"mean": None, "std": None, "count": 0, "sum": None}

        mean = statistics.mean(sample)
        std = statistics.stdev(sample) if len(sample) >= 2 else 0.0

        return {
            "mean": mean,
            "std": std,
            "count": len(sample),
            "sum": sum(sample),
        }

    def _t_distribution_pvalue(self, t: float, df: float) -> float:
        """t分布の両側p値を計算する（近似）。"""
        # ベータ関数による近似
        x = df / (df + t * t)
        return 2 * self._incomplete_beta(x, df / 2, 0.5)

    def _t_critical_value(self, alpha: float, df: int) -> float:
        """t分布の臨界値を返す（常用値のテーブル）。"""
        # 95%信頼区間用の臨界値テーブル（両側 alpha=0.025）
        t_table = {
            1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
            6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
            15: 2.131, 20: 2.086, 30: 2.042, 60: 2.000, 120: 1.980,
        }

        if df in t_table:
            return t_table[df]
        elif df > 120:
            return 1.96  # 正規分布近似
        else:
            # 線形補間
            lower_df = max(k for k in t_table.keys() if k <= df)
            upper_df = min(k for k in t_table.keys() if k >= df)
            if lower_df == upper_df:
                return t_table[lower_df]
            ratio = (df - lower_df) / (upper_df - lower_df)
            return t_table[lower_df] + ratio * (t_table[upper_df] - t_table[lower_df])

    def _incomplete_beta(self, x: float, a: float, b: float) -> float:
        """不完全ベータ関数の近似（連分数展開）。"""
        if x == 0:
            return 0.0
        if x == 1:
            return 1.0

        # 連分数展開による近似
        max_iter = 200
        eps = 1e-10

        # 前処理
        qab = a + b
        qap = a + 1.0
        qam = a - 1.0
        c = 1.0
        d = 1.0 - qab * x / qap
        if abs(d) < eps:
            d = eps
        d = 1.0 / d
        h = d

        for m in range(1, max_iter + 1):
            m2 = 2 * m

            # 偶数ステップ
            aa = m * (b - m) * x / ((qam + m2) * (a + m2))
            d = 1.0 + aa * d
            if abs(d) < eps:
                d = eps
            c = 1.0 + aa / c
            if abs(c) < eps:
                c = eps
            d = 1.0 / d
            h *= d * c

            # 奇数ステップ
            aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
            d = 1.0 + aa * d
            if abs(d) < eps:
                d = eps
            c = 1.0 + aa / c
            if abs(c) < eps:
                c = eps
            d = 1.0 / d
            delta = d * c
            h *= delta

            if abs(delta - 1.0) < eps:
                break

        # ベータ関数の対数
        log_beta = (
            math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
        )

        # 最終値
        front = math.exp(
            a * math.log(x) + b * math.log(1.0 - x) - log_beta
        ) / a

        return front * h
