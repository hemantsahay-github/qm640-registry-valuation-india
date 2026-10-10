"""
sample_size.py — Reproducible sample-size calculations for RQ1–RQ4.

Purpose : Recompute every minimum N reported in the synopsis (Table 4) so a
          mentor can verify the arithmetic. Prints a step-by-step trace and
          writes outputs/sample_size.csv.
Run     : python scripts/sample_size.py
Author  : Hemant Kumar Sahay (QM 640 Data Analytics Capstone, Walsh College)
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
from scipy import stats

ALPHA = 0.05            # two-sided significance level for all RQs
POWER = 0.80            # target power where power analysis applies
Z_A = stats.norm.ppf(1 - ALPHA / 2)   # 1.959964
Z_B = stats.norm.ppf(POWER)           # 0.841621


def rq1_ci_proportion(p: float = 0.50, e: float = 0.03) -> int:
    """Precision of the anchored share: n = Z^2 p(1-p) / e^2."""
    n = Z_A ** 2 * p * (1 - p) / e ** 2
    print(f"RQ1  n = {Z_A:.4f}^2 x {p} x {1-p} / {e}^2 = {n:.2f} -> {math.ceil(n)}")
    return math.ceil(n)


def rq2_f_test_r2_increase(f2: float = 0.02, u: int = 11, k: int = 12) -> int:
    """Smallest N with power >= .80 for the partial F test of R^2 change.
    Cohen (1988): lambda = f2 * N; df1 = u; df2 = N - k - 1."""
    for n in range(k + 2, 5000):
        df2 = n - k - 1
        lam = f2 * n
        f_crit = stats.f.ppf(1 - ALPHA, u, df2)
        power = 1 - stats.ncf.cdf(f_crit, u, df2, lam)
        if power >= POWER:
            print(f"RQ2  N = {n}: lambda = {lam:.2f}, F_crit({u},{df2}) = {f_crit:.3f}, power = {power:.4f}")
            return n
    raise RuntimeError("no N found")


def rq3_paired_t(d: float = 0.20, test_share: float = 0.20) -> tuple[int, int]:
    """Paired t test on absolute errors (Guenther correction), then gross-up
    for the share of micro-markets held out for testing."""
    n = ((Z_A + Z_B) / d) ** 2 + Z_A ** 2 / 2
    n_test = math.ceil(n)
    n_total = math.ceil(n_test / test_share)
    print(f"RQ3  n_test = ({Z_A + Z_B:.4f}/{d})^2 + {Z_A**2/2:.2f} = {n:.2f} -> {n_test}; "
          f"N = {n_test}/{test_share} = {n_total}")
    return n_test, n_total


def rq4_logistic(p_event: float = 0.12, odds_ratio: float = 1.5,
                 rho2: float = 0.30, n_pred: int = 12, epv: int = 10) -> int:
    """Hsieh et al. (1998) for a standardized continuous predictor, inflated by
    1/(1-rho^2) for correlated covariates; compared with the EPV rule
    (Peduzzi et al., 1996). The larger value is adopted."""
    b = math.log(odds_ratio)
    n_h = (Z_A + Z_B) ** 2 / (p_event * (1 - p_event) * b ** 2)
    n_adj = math.ceil(n_h / (1 - rho2))
    n_epv = math.ceil(epv * n_pred / p_event)
    print(f"RQ4  Hsieh n = {(Z_A+Z_B)**2:.4f} / ({p_event} x {1-p_event:.2f} x {b**2:.4f}) = {n_h:.2f}; "
          f"/ (1 - {rho2}) = {n_adj}; EPV = {epv} x {n_pred} / {p_event} = {n_epv}")
    return max(n_adj, n_epv)


def main() -> None:
    n1 = rq1_ci_proportion()
    n2 = rq2_f_test_r2_increase()
    _, n3 = rq3_paired_t()
    n4 = rq4_logistic()
    final = max(n1, n2, n3, n4)
    collect = math.ceil(final / 0.60 / 100) * 100   # allow 40% exclusions
    print(f"FINAL N = max({n1}, {n2}, {n3}, {n4}) = {final}; collection target = {collect}")
    out = pd.DataFrame({"rq": ["RQ1", "RQ2", "RQ3", "RQ4", "FINAL"],
                        "min_n": [n1, n2, n3, n4, final]})
    Path("outputs").mkdir(exist_ok=True)
    out.to_csv("outputs/sample_size.csv", index=False)


if __name__ == "__main__":
    main()
