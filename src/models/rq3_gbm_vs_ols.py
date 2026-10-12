"""
rq3_gbm_vs_ols.py — RQ3: Does gradient-boosted regression predict
ln(registered consideration per m2) with lower absolute error than the OLS
hedonic baseline on micro-markets withheld from training?

Method
  1. Hold out ~20% of MICRO-MARKETS (GroupShuffleSplit), so test locations are
     completely unseen (Roberts et al., 2017).
  2. OLS baseline = RQ2 full model (12 predictors).
     XGBoost = same 12 predictors + latitude/longitude (Chen & Guestrin, 2016).
  3. XGBoost hyper-parameters tuned by randomized search with 5-fold
     GroupKFold on the training micro-markets (objective: MAE).
  4. Test-set metrics (Equations 3-4): RMSE, MAE, R2 on the log scale and
     RMSE, MAE, MAPE on the rupee scale (value per m2).
  5. Paired comparison of absolute errors, d_i = |e_OLS| - |e_XGB| (Equation 5):
     paired t test (H1: mean d > 0), Wilcoxon signed-rank, Diebold-Mariano
     (absolute loss, Harvey-Leybourne-Newbold correction), plus a cluster
     bootstrap over test micro-markets because errors within a locality are
     correlated.
  6. Robustness: 5-fold grouped CV over ALL micro-markets for both models.
  7. Explainability: SHAP values (Lundberg & Lee, 2017) on the test set.
  8. Bias audit: MAE by district, price band and new-sale status.
Outputs : outputs/rq3/*.csv, *.png, xgb_model.json, best_params.json, summary.json
"""
from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import statsmodels.api as sm
from scipy import stats
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, RandomizedSearchCV
from xgboost import XGBRegressor

from src.config import ALPHA, ANALYSIS_FILE, OUTPUT_DIR, RANDOM_SEED, TEST_GROUP_SHARE
from src.models.rq2_hedonic import LABELS, design
from src.utils.plotstyle import INK_2, SERIES, footer

OUT = OUTPUT_DIR / "rq3"
Y = "ln_value_m2"
PARAM_GRID = {"max_depth": [2, 3, 4, 5, 6], "learning_rate": [0.02, 0.05, 0.1],
              "n_estimators": [200, 400, 800], "min_child_weight": [1, 3, 5, 10],
              "subsample": [0.7, 0.85, 1.0], "colsample_bytree": [0.7, 0.85, 1.0],
              "reg_lambda": [0.5, 1.0, 5.0]}


def features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    X_ols = design(df)
    X_xgb = X_ols.copy()
    X_xgb["lat"], X_xgb["lon"] = df["lat"].to_numpy(), df["lon"].to_numpy()
    return X_ols, X_xgb


def metrics(y_log: np.ndarray, p_log: np.ndarray) -> dict:
    e = y_log - p_log
    y_r, p_r = np.exp(y_log), np.exp(p_log)
    return {"RMSE_log": float(np.sqrt(np.mean(e ** 2))), "MAE_log": float(np.mean(np.abs(e))),
            "R2_log": float(1 - np.sum(e ** 2) / np.sum((y_log - y_log.mean()) ** 2)),
            "RMSE_inr_m2": float(np.sqrt(np.mean((y_r - p_r) ** 2))),
            "MAE_inr_m2": float(np.mean(np.abs(y_r - p_r))),
            "MAPE_pct": float(100 * np.mean(np.abs((y_r - p_r) / y_r)))}


def diebold_mariano(d: np.ndarray) -> tuple[float, float]:
    """DM test on loss differential d (h = 1) with HLN small-sample correction;
    one-sided H1: OLS loss > XGB loss."""
    n = len(d)
    dm = d.mean() / np.sqrt(d.var(ddof=0) / n)
    hln = dm * np.sqrt((n - 1) / n)
    return float(hln), float(stats.t.sf(hln, df=n - 1))


def cluster_bootstrap(d: np.ndarray, groups: np.ndarray, reps: int = 2000, seed: int = RANDOM_SEED):
    rng = np.random.default_rng(seed)
    ug = np.unique(groups)
    idx = {g: np.where(groups == g)[0] for g in ug}
    means = []
    for _ in range(reps):
        pick = rng.choice(ug, size=len(ug), replace=True)
        means.append(np.concatenate([d[idx[g]] for g in pick]).mean())
    return np.percentile(means, [2.5, 97.5]), float(np.mean(np.array(means) <= 0))


def run(label: str) -> tuple[dict, list]:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(ANALYSIS_FILE)
    X_ols, X_xgb = features(df)
    y, groups = df[Y].to_numpy(), df["micro_market"].to_numpy()

    gss = GroupShuffleSplit(n_splits=1, test_size=TEST_GROUP_SHARE, random_state=RANDOM_SEED)
    tr, te = next(gss.split(X_ols, y, groups))
    test_markets = sorted(set(groups[te]))

    # ---- OLS baseline
    ols = sm.OLS(y[tr], sm.add_constant(X_ols.iloc[tr])).fit()
    p_ols = ols.predict(sm.add_constant(X_ols.iloc[te], has_constant="add")).to_numpy()

    # ---- XGBoost with grouped CV tuning
    search = RandomizedSearchCV(
        XGBRegressor(objective="reg:squarederror", random_state=RANDOM_SEED, n_jobs=4, tree_method="hist"),
        PARAM_GRID, n_iter=30, scoring="neg_mean_absolute_error", cv=GroupKFold(n_splits=5),
        random_state=RANDOM_SEED, n_jobs=1)
    search.fit(X_xgb.iloc[tr], y[tr], groups=groups[tr])
    xgb = search.best_estimator_
    p_xgb = xgb.predict(X_xgb.iloc[te])
    xgb.save_model(OUT / "xgb_model.json")
    (OUT / "best_params.json").write_text(json.dumps(search.best_params_, indent=2))

    m_ols, m_xgb = metrics(y[te], p_ols), metrics(y[te], p_xgb)
    met = pd.DataFrame({"OLS": m_ols, "XGBoost": m_xgb}).round(5)
    met["improvement_pct"] = (100 * (met["OLS"] - met["XGBoost"]) / met["OLS"].abs()).round(2)
    met.loc["R2_log", "improvement_pct"] = np.nan
    met.to_csv(OUT / "rq3_test_metrics.csv")

    # ---- paired tests on absolute log errors
    e_o, e_x = np.abs(y[te] - p_ols), np.abs(y[te] - p_xgb)
    d = e_o - e_x
    t_stat, p_t_two = stats.ttest_rel(e_o, e_x)
    p_t_one = float(p_t_two / 2 if t_stat > 0 else 1 - p_t_two / 2)
    w = stats.wilcoxon(e_o, e_x, alternative="greater")
    dm, p_dm = diebold_mariano(d)
    (cb_lo, cb_hi), p_cb = cluster_bootstrap(d, groups[te])
    tests = {"n_test": int(len(te)), "mean_d": float(d.mean()), "sd_d": float(d.std(ddof=1)),
             "cohens_dz": float(d.mean() / d.std(ddof=1)),
             "paired_t": float(t_stat), "df": int(len(te) - 1), "p_t_one_sided": p_t_one,
             "wilcoxon_W": float(w.statistic), "p_wilcoxon_one_sided": float(w.pvalue),
             "dm_hln": dm, "p_dm_one_sided": p_dm,
             "cluster_boot_ci95_mean_d": [float(cb_lo), float(cb_hi)], "p_cluster_boot": p_cb,
             "share_cases_xgb_better": float((d > 0).mean())}
    pd.Series(tests).to_csv(OUT / "rq3_paired_tests.csv", header=["value"])

    # ---- robustness: grouped 5-fold CV over all data
    cv_rows = []
    for f, (a, b) in enumerate(GroupKFold(n_splits=5).split(X_ols, y, groups)):
        o = sm.OLS(y[a], sm.add_constant(X_ols.iloc[a])).fit()
        po = o.predict(sm.add_constant(X_ols.iloc[b], has_constant="add")).to_numpy()
        xm = XGBRegressor(objective="reg:squarederror", random_state=RANDOM_SEED, n_jobs=4,
                          tree_method="hist", **search.best_params_).fit(X_xgb.iloc[a], y[a])
        px = xm.predict(X_xgb.iloc[b])
        cv_rows.append({"fold": f + 1, "n": len(b), "MAE_log_OLS": np.mean(np.abs(y[b] - po)),
                        "MAE_log_XGB": np.mean(np.abs(y[b] - px)),
                        "MAPE_OLS": metrics(y[b], po)["MAPE_pct"], "MAPE_XGB": metrics(y[b], px)["MAPE_pct"]})
    cv = pd.DataFrame(cv_rows).round(5)
    cv.to_csv(OUT / "rq3_grouped_cv.csv", index=False)

    # ---- bias audit by segment
    te_df = df.iloc[te].copy()
    te_df["abs_err_OLS"], te_df["abs_err_XGB"] = e_o, e_x
    te_df["price_band"] = pd.qcut(te_df["value_m2"], 3, labels=["low", "mid", "high"])
    audit = []
    for seg in ["district", "price_band", "new_sale", "anchored"]:
        g = te_df.groupby(seg, observed=True)[["abs_err_OLS", "abs_err_XGB"]].mean()
        for lvl, r in g.iterrows():
            audit.append({"segment": seg, "level": str(lvl), "n": int((te_df[seg] == lvl).sum()),
                          "MAE_log_OLS": r["abs_err_OLS"], "MAE_log_XGB": r["abs_err_XGB"]})
    audit = pd.DataFrame(audit).round(5)
    audit.to_csv(OUT / "rq3_bias_audit.csv", index=False)
    pd.DataFrame({"micro_market": groups[te], "y": y[te], "pred_ols": p_ols, "pred_xgb": p_xgb}
                 ).round(5).to_csv(OUT / "rq3_test_predictions.csv", index=False)

    # ---- SHAP
    expl = shap.TreeExplainer(xgb)
    sv = expl.shap_values(X_xgb.iloc[te])
    names = [LABELS.get(c, {"lat": "Latitude", "lon": "Longitude"}.get(c, c)) for c in X_xgb.columns]
    imp = pd.DataFrame({"feature": names, "mean_abs_shap": np.abs(sv).mean(axis=0)}
                       ).sort_values("mean_abs_shap", ascending=False).round(5)
    imp.to_csv(OUT / "rq3_shap_importance.csv", index=False)
    plt.figure()
    shap.summary_plot(sv, X_xgb.iloc[te].set_axis(names, axis=1), show=False, max_display=14)
    fig = plt.gcf(); fig.set_size_inches(9, 6)
    plt.title("RQ3 — SHAP values on held-out micro-markets", fontweight="bold")
    footer(fig, label); fig.savefig(OUT / "fig_rq3_shap_beeswarm.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    top = imp.head(13)[::-1]
    ax.barh(top["feature"], top["mean_abs_shap"], color=SERIES[0])
    ax.set_xlabel("Mean |SHAP value| (log points)"); ax.set_title("RQ3 — Feature importance (XGBoost)")
    footer(fig, label); fig.savefig(OUT / "fig_rq3_shap_importance.png"); plt.close(fig)

    # ---- comparison figures
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharex=True, sharey=True)
    lo, hi = y[te].min(), y[te].max()
    for ax, p, name, col, m in [(axes[0], p_ols, "OLS hedonic", INK_2, m_ols), (axes[1], p_xgb, "XGBoost", SERIES[0], m_xgb)]:
        ax.scatter(y[te], p, s=9, alpha=0.5, color=col)
        ax.plot([lo, hi], [lo, hi], color=SERIES[1], lw=1.3, ls="--")
        ax.set_title(f"{name}: MAE = {m['MAE_log']:.4f}, MAPE = {m['MAPE_pct']:.2f}%")
        ax.set_xlabel("Actual ln value per m²")
    axes[0].set_ylabel("Predicted ln value per m²")
    fig.suptitle("RQ3 — Predictions on held-out micro-markets", fontweight="bold")
    fig.tight_layout(); footer(fig, label); fig.savefig(OUT / "fig_rq3_pred_vs_actual.png"); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    bins = np.linspace(0, max(e_o.max(), e_x.max()), 40)
    axes[0].hist(e_o, bins=bins, alpha=0.6, color=INK_2, label="OLS")
    axes[0].hist(e_x, bins=bins, alpha=0.6, color=SERIES[0], label="XGBoost")
    axes[0].set_title("Absolute errors (log scale)"); axes[0].set_xlabel("|error|"); axes[0].legend()
    axes[1].hist(d, bins=40, color=SERIES[0], alpha=0.8)
    axes[1].axvline(0, color=INK_2, lw=1.3); axes[1].axvline(d.mean(), color=SERIES[1], lw=2, label=f"mean d = {d.mean():.4f}")
    axes[1].set_title("Paired difference d = |e_OLS| − |e_XGB|"); axes[1].legend()
    fig.tight_layout(); footer(fig, label); fig.savefig(OUT / "fig_rq3_error_comparison.png"); plt.close(fig)

    better = p_t_one < ALPHA and d.mean() > 0
    summary = {
        "n_train": int(len(tr)), "n_test": int(len(te)), "min_test_required": 199,
        "test_micro_markets": test_markets, "n_test_micro_markets": len(test_markets),
        "best_params": search.best_params_, "cv_MAE_log_best": round(float(-search.best_score_), 5),
        "test_metrics_OLS": {k: round(v, 4) for k, v in m_ols.items()},
        "test_metrics_XGB": {k: round(v, 4) for k, v in m_xgb.items()},
        "paired_tests": {k: (round(v, 5) if isinstance(v, float) else v) for k, v in tests.items()},
        "decision_alpha_0.05": ("Reject H0: XGBoost has lower absolute error than OLS" if better
                                else "Fail to reject H0: no significant advantage for XGBoost"),
        "grouped_cv_mean_MAE_log": {"OLS": round(float(cv["MAE_log_OLS"].mean()), 5),
                                    "XGB": round(float(cv["MAE_log_XGB"].mean()), 5),
                                    "folds_xgb_better": int((cv["MAE_log_XGB"] < cv["MAE_log_OLS"]).sum())},
        "top5_shap": imp.head(5)["feature"].tolist(),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=float))
    return summary, sorted(OUT.iterdir())
