"""
rq1_bunching.py — RQ1: To what extent do registered consideration values bunch
at the ASR-implied market value, and what share of transactions is excess mass?

Method  : Bunching estimator (Chetty et al., 2011; Kleven, 2016).
  1. Bin R = consideration / ASR value in widths of 0.01 over [0.80, 2.00).
  2. Fit a degree-7 polynomial to bin counts EXCLUDING the window [0.98, 1.02).
  3. Integration constraint: bunchers come from above the window, so counts to
     the right are scaled up until the counterfactual integrates to the
     observed total (iterative fixed point).
  4. Excess mass  B = sum_W (c_j - c_hat_j);  normalised b = B / mean_W(c_hat_j)
     (Equation 1 in the synopsis);  excess share = B / N.
  5. 500 bootstrap re-samples of transactions -> 95% percentile CI and one-sided
     p-value for H0: b = 0 vs H1: b > 0.
  6. Robustness: polynomial degree 5-9; window +/-1% and +/-5%; round-number
     dummies; separate estimates by district and by financial year.
Outputs : outputs/rq1/*.csv, *.png, summary.json
"""
from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src.config import (ANALYSIS_FILE, ANCHOR_HI, ANCHOR_LO, BIN_WIDTH, BOOTSTRAP_REPS,
                        BUNCH_RANGE, OUTPUT_DIR, POLY_DEGREE, RANDOM_SEED)
from src.utils.plotstyle import DISTRICT_COLOR, INK_2, SERIES, footer

OUT = OUTPUT_DIR / "rq1"


def bin_counts(r: np.ndarray, width: float = BIN_WIDTH, rng_: tuple = BUNCH_RANGE):
    edges = np.round(np.arange(rng_[0], rng_[1] + width / 2, width), 4)
    counts, _ = np.histogram(r, bins=edges)
    return edges[:-1], counts.astype(float)            # left edges, counts


def estimate(r: np.ndarray, degree: int = POLY_DEGREE, lo: float = ANCHOR_LO,
             hi: float = ANCHOR_HI, round_dummies: bool = False, max_iter: int = 200) -> dict:
    left, c = bin_counts(r)
    z = left + BIN_WIDTH / 2
    in_w = (left >= lo - 1e-9) & (left < hi - 1e-9)
    above = left >= hi - 1e-9
    X = np.vander((z - 1.4) / 0.6, degree + 1, increasing=True)    # scaled for conditioning
    if round_dummies:  # bins starting at 1.10, 1.20, ... absorb round-number heaping
        rd = np.isclose((left * 10) % 1, 0, atol=1e-6) & ~in_w & (left > hi)
        X = np.column_stack([X] + [rd & np.isclose(left, v) for v in left[rd]])
    keep = ~in_w
    c_adj, B = c.copy(), 0.0
    for _ in range(max_iter):
        beta, *_ = np.linalg.lstsq(X[keep], c_adj[keep], rcond=None)
        c_hat = X[:, : degree + 1] @ beta[: degree + 1]               # smooth counterfactual
        B_new = float((c[in_w] - c_hat[in_w]).sum())
        c_adj = c.copy()
        c_adj[above] = c[above] * (1 + B_new / c[above].sum())       # integration constraint
        if abs(B_new - B) < 1e-6:
            break
        B = B_new
    b = B / c_hat[in_w].mean()
    return {"B_excess_count": B, "b_normalised": b, "excess_share": B / len(r),
            "window_observed": float(c[in_w].sum()), "window_counterfactual": float(c_hat[in_w].sum()),
            "n_bins_window": int(in_w.sum()), "_z": z, "_c": c, "_c_hat": c_hat, "_in_w": in_w}


def bootstrap(r: np.ndarray, reps: int = BOOTSTRAP_REPS, seed: int = RANDOM_SEED) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.array([estimate(rng.choice(r, size=len(r), replace=True))["b_normalised"]
                     for _ in range(reps)])


def wilson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    z = stats.norm.ppf(1 - alpha / 2)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def _plot(res: dict, ax, title: str, color: str) -> None:
    z, c, ch, w = res["_z"], res["_c"], res["_c_hat"], res["_in_w"]
    ax.bar(z, c, width=BIN_WIDTH * 0.9, color=color, alpha=0.75, label="Observed count")
    ax.plot(z, ch, color=INK_2, lw=2, label=f"Counterfactual (poly {POLY_DEGREE})")
    ax.axvspan(z[w].min() - BIN_WIDTH / 2, z[w].max() + BIN_WIDTH / 2, color=SERIES[1], alpha=0.18,
               label="Excluded window")
    ax.set_title(title); ax.set_xlabel("R = consideration / ASR value"); ax.set_ylabel("Transactions")
    ax.text(0.98, 0.95, f"b = {res['b_normalised']:.2f}\nexcess share = {res['excess_share']:.1%}",
            transform=ax.transAxes, ha="right", va="top", fontsize=9,
            bbox=dict(boxstyle="round", fc="white", ec="#d0cfc9"))


def run(label: str) -> tuple[dict, list]:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(ANALYSIS_FILE)
    r = df["r_ratio"].to_numpy()
    r_in = r[(r >= BUNCH_RANGE[0]) & (r < BUNCH_RANGE[1])]

    main = estimate(r_in)
    boots = bootstrap(r_in)
    ci_lo, ci_hi = np.percentile(boots, [2.5, 97.5])
    p_one_sided = float((boots <= 0).mean())
    k, n = int(df["anchored"].sum()), len(df)
    a_lo, a_hi = wilson_ci(k, n)

    # robustness grid
    rob = []
    for deg in range(5, 10):
        for lo, hi, wname in [(0.99, 1.01, "±1%"), (ANCHOR_LO, ANCHOR_HI, "±2% (main)"), (0.95, 1.05, "±5%")]:
            e = estimate(r_in, degree=deg, lo=lo, hi=hi)
            rob.append({"degree": deg, "window": wname, "b": round(e["b_normalised"], 3),
                        "excess_share": round(e["excess_share"], 4)})
    e_rd = estimate(r_in, round_dummies=True)
    rob.append({"degree": POLY_DEGREE, "window": "±2% + round-number dummies",
                "b": round(e_rd["b_normalised"], 3), "excess_share": round(e_rd["excess_share"], 4)})
    rob_df = pd.DataFrame(rob)
    rob_df.to_csv(OUT / "rq1_robustness.csv", index=False)

    # by district and FY
    seg = []
    for col in ["district", "fy"]:
        for lvl, g in df.groupby(col):
            rr = g["r_ratio"].to_numpy()
            rr = rr[(rr >= BUNCH_RANGE[0]) & (rr < BUNCH_RANGE[1])]
            e = estimate(rr)
            lo_, hi_ = wilson_ci(int(g["anchored"].sum()), len(g))
            seg.append({"segment": col, "level": lvl, "n": len(g), "anchored_share": round(g["anchored"].mean(), 4),
                        "anchored_ci95": f"[{lo_:.3f}, {hi_:.3f}]", "b": round(e["b_normalised"], 3),
                        "excess_share": round(e["excess_share"], 4)})
    seg_df = pd.DataFrame(seg)
    seg_df.to_csv(OUT / "rq1_by_segment.csv", index=False)

    pd.DataFrame({"bin_left": main["_z"] - BIN_WIDTH / 2, "observed": main["_c"],
                  "counterfactual": main["_c_hat"].round(2), "in_window": main["_in_w"]}
                 ).to_csv(OUT / "rq1_bins.csv", index=False)

    # figures
    fig, ax = plt.subplots(figsize=(10, 4.8))
    _plot(main, ax, "RQ1 — Bunching of registered value at the ASR threshold (pooled)", SERIES[0])
    ax.legend(loc="center right"); footer(fig, label)
    fig.savefig(OUT / "fig_rq1_bunching_pooled.png"); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(14, 4.5), sharey=False)
    for ax, (d, g) in zip(axes, df.groupby("district")):
        rr = g["r_ratio"].to_numpy()
        _plot(estimate(rr[(rr >= BUNCH_RANGE[0]) & (rr < BUNCH_RANGE[1])]), ax, f"{d}", DISTRICT_COLOR[d])
    fig.suptitle("RQ1 — Bunching by district", fontweight="bold"); fig.tight_layout(); footer(fig, label)
    fig.savefig(OUT / "fig_rq1_bunching_by_district.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(boots, bins=40, color=SERIES[0], alpha=0.8)
    ax.axvline(main["b_normalised"], color=INK_2, lw=2, label="Point estimate")
    ax.axvline(ci_lo, color=SERIES[1], ls="--", lw=1.5, label="95% CI")
    ax.axvline(ci_hi, color=SERIES[1], ls="--", lw=1.5)
    ax.set_title(f"RQ1 — Bootstrap distribution of b ({BOOTSTRAP_REPS} reps)"); ax.set_xlabel("b"); ax.legend()
    footer(fig, label); fig.savefig(OUT / "fig_rq1_bootstrap.png"); plt.close(fig)

    summary = {
        "n_analysed": int(n), "n_in_bunching_range": int(len(r_in)),
        "window": f"[{ANCHOR_LO}, {ANCHOR_HI})", "bins_in_window": main["n_bins_window"],
        "observed_in_window": main["window_observed"],
        "counterfactual_in_window": round(main["window_counterfactual"], 1),
        "excess_count_B": round(main["B_excess_count"], 1),
        "b_normalised": round(main["b_normalised"], 3),
        "b_bootstrap_ci95": [round(float(ci_lo), 3), round(float(ci_hi), 3)],
        "p_value_H0_b_eq_0_one_sided": p_one_sided,
        "decision_alpha_0.05": "Reject H0 (bunching present)" if p_one_sided < 0.05 else "Fail to reject H0",
        "excess_share_of_transactions": round(main["excess_share"], 4),
        "anchored_share_observed": round(k / n, 4), "anchored_share_ci95_wilson": [round(float(a_lo), 4), round(float(a_hi), 4)],
        "ci_half_width": round(float(a_hi - a_lo) / 2, 4),
        "robustness_b_range": [float(rob_df["b"].min()), float(rob_df["b"].max())],
        "by_segment": seg_df[["segment", "level", "n", "anchored_share", "b"]].to_dict("records"),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary, sorted(OUT.iterdir())
