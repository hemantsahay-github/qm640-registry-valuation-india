"""
rq4_anchoring.py — RQ4: Which characteristics predict whether a transaction is
registered at the ASR threshold, and what micro-market correction factor does
the best value model imply for anchored transactions?

Part A — Anchoring classification (anchored = 1 if 0.98 <= R < 1.02)
  1. Logistic regression (primary) on the 12 RQ2 predictors: odds ratios with
     95% CI, likelihood-ratio test vs. the null model, McFadden pseudo-R2,
     events-per-variable check, Box-Tidwell linearity-in-the-logit test.
  2. XGBoost classifier (benchmark), tuned with grouped CV.
  3. Both evaluated on the SAME held-out micro-markets as RQ3:
     AUC, Brier score, precision, recall, F1 (Equations 6-7); the decision
     threshold is chosen on the training data (Youden J), never on test data.
Part B — Correction factor (Equation 8)
  4. The best RQ3 value model (chosen from rq3/summary.json) is retrained on
     NON-anchored transactions only, then predicts value for anchored ones.
  5. CF_i = predicted value / registered value;  CF_m = median over anchored
     transactions in micro-market m, with a bootstrap 95% CI.
     Reported only where n_anchored >= MIN_ANCHORED_FOR_CF (20); never at the
     level of an individual transaction.
  6. Direction check against NHB RESIDEX when data/external/residex/residex.csv
     is present.
Outputs : outputs/rq4/*.csv, *.png, correction_factors.csv (Estima schema), summary.json
"""
from __future__ import annotations

import json
from datetime import date

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.metrics import (brier_score_loss, confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, RandomizedSearchCV
from xgboost import XGBClassifier, XGBRegressor

from src.config import (ALPHA, ANALYSIS_FILE, EXTERNAL_DIR, MIN_ANCHORED_FOR_CF, OUTPUT_DIR,
                        RANDOM_SEED, TEST_GROUP_SHARE)
from src.models.rq2_hedonic import LABELS, design
from src.models.rq3_gbm_vs_ols import features
from src.utils.plotstyle import INK_2, SERIES, footer

OUT = OUTPUT_DIR / "rq4"
MODEL_VERSION = "rq4-v1.0"
CONTINUOUS_POS = ["ln_asr_rate_m2", "ln_carpet_area", "dist_rail_km", "dist_cbd_km"]


def classification_metrics(y, p, thr) -> dict:
    yhat = (p >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, yhat, labels=[0, 1]).ravel()
    return {"AUC": float(roc_auc_score(y, p)), "Brier": float(brier_score_loss(y, p)),
            "threshold": float(thr), "precision": float(precision_score(y, yhat, zero_division=0)),
            "recall": float(recall_score(y, yhat, zero_division=0)), "F1": float(f1_score(y, yhat, zero_division=0)),
            "TP": int(tp), "FP": int(fp), "FN": int(fn), "TN": int(tn)}


def youden_threshold(y, p) -> float:
    fpr, tpr, thr = roc_curve(y, p)
    return float(thr[np.argmax(tpr - fpr)])


def box_tidwell(y, X) -> pd.DataFrame:
    """Add x*ln(x) for each positive continuous predictor; a significant term
    signals non-linearity in the logit."""
    Xb = X.copy()
    rows = []
    for v in CONTINUOUS_POS:
        x = X[v] + (1e-3 if (X[v] <= 0).any() else 0)
        Xb[f"{v}_xlnx"] = x * np.log(x)
    m = sm.Logit(y, sm.add_constant(Xb)).fit(disp=0, maxiter=200)
    for v in CONTINUOUS_POS:
        rows.append({"variable": v, "b_xlnx": m.params[f"{v}_xlnx"], "p": m.pvalues[f"{v}_xlnx"],
                     "linear_in_logit_ok": m.pvalues[f"{v}_xlnx"] >= ALPHA})
    return pd.DataFrame(rows)


def bootstrap_median_ci(x: np.ndarray, reps: int = 1000, seed: int = RANDOM_SEED):
    rng = np.random.default_rng(seed)
    meds = [np.median(rng.choice(x, len(x), replace=True)) for _ in range(reps)]
    return np.percentile(meds, [2.5, 97.5])


def run(label: str) -> tuple[dict, list]:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(ANALYSIS_FILE)
    X, y, groups = design(df), df["anchored"].to_numpy(), df["micro_market"].to_numpy()
    n_events, k = int(y.sum()), X.shape[1]

    # ------------------------------------------------------------ Part A: logit (full sample, inference)
    logit = sm.Logit(y, sm.add_constant(X)).fit(disp=0, maxiter=200)
    ci = logit.conf_int(alpha=ALPHA)
    orr = pd.DataFrame({"term": [LABELS[t] for t in logit.params.index], "variable": logit.params.index,
                        "b": logit.params, "se": logit.bse, "z": logit.tvalues, "p": logit.pvalues,
                        "odds_ratio": np.exp(logit.params), "or_ci95_low": np.exp(ci[0]),
                        "or_ci95_high": np.exp(ci[1])})
    orr["significant"] = orr["p"] < ALPHA
    orr.round(5).to_csv(OUT / "rq4_logit_odds_ratios.csv", index=False)
    lr_stat, lr_df = float(logit.llr), int(logit.df_model)
    bt = box_tidwell(y, X)
    bt.round(5).to_csv(OUT / "rq4_box_tidwell.csv", index=False)
    (OUT / "rq4_logit_summary.txt").write_text(f"{label}\n\n{logit.summary()}")

    # ------------------------------------------------------------ Part A: out-of-sample (same split as RQ3)
    gss = GroupShuffleSplit(n_splits=1, test_size=TEST_GROUP_SHARE, random_state=RANDOM_SEED)
    tr, te = next(gss.split(X, y, groups))
    lg_tr = sm.Logit(y[tr], sm.add_constant(X.iloc[tr])).fit(disp=0, maxiter=200)
    p_lg_tr = lg_tr.predict(sm.add_constant(X.iloc[tr]))
    p_lg = lg_tr.predict(sm.add_constant(X.iloc[te], has_constant="add")).to_numpy()
    thr_lg = youden_threshold(y[tr], p_lg_tr)

    _, X_xgb = features(df)
    search = RandomizedSearchCV(
        XGBClassifier(objective="binary:logistic", eval_metric="logloss", random_state=RANDOM_SEED,
                      n_jobs=4, tree_method="hist"),
        {"max_depth": [2, 3, 4, 5], "learning_rate": [0.03, 0.05, 0.1], "n_estimators": [200, 400],
         "min_child_weight": [1, 5, 10], "subsample": [0.8, 1.0], "colsample_bytree": [0.8, 1.0]},
        n_iter=20, scoring="roc_auc", cv=GroupKFold(n_splits=5), random_state=RANDOM_SEED, n_jobs=1)
    search.fit(X_xgb.iloc[tr], y[tr], groups=groups[tr])
    xgbc = search.best_estimator_
    p_xg_tr = xgbc.predict_proba(X_xgb.iloc[tr])[:, 1]
    p_xg = xgbc.predict_proba(X_xgb.iloc[te])[:, 1]
    thr_xg = youden_threshold(y[tr], p_xg_tr)

    cm_lg, cm_xg = classification_metrics(y[te], p_lg, thr_lg), classification_metrics(y[te], p_xg, thr_xg)
    cls = pd.DataFrame({"Logistic": cm_lg, "XGBoost": cm_xg})
    cls.to_csv(OUT / "rq4_classification_test_metrics.csv")
    # DeLong-free AUC comparison: bootstrap difference
    rng = np.random.default_rng(RANDOM_SEED)
    diffs = []
    for _ in range(1000):
        i = rng.choice(len(te), len(te), replace=True)
        if y[te][i].min() == y[te][i].max():
            continue
        diffs.append(roc_auc_score(y[te][i], p_xg[i]) - roc_auc_score(y[te][i], p_lg[i]))
    auc_diff_ci = np.percentile(diffs, [2.5, 97.5])

    # ------------------------------------------------------------ Part B: correction factor
    rq3 = json.loads((OUTPUT_DIR / "rq3" / "summary.json").read_text())
    use_xgb = rq3["decision_alpha_0.05"].startswith("Reject")
    non, anc = df["anchored"] == 0, df["anchored"] == 1
    X_ols, X_x = design(df), X_xgb
    if use_xgb:
        params = json.loads((OUTPUT_DIR / "rq3" / "best_params.json").read_text())
        vm = XGBRegressor(objective="reg:squarederror", random_state=RANDOM_SEED, tree_method="hist", **params)
        vm.fit(X_x[non], df.loc[non, "ln_value_m2"])
        pred_ln = vm.predict(X_x[anc])
        value_model = "XGBoost (RQ3 winner)"
    else:
        vm = sm.OLS(df.loc[non, "ln_value_m2"], sm.add_constant(X_ols[non])).fit()
        pred_ln = vm.predict(sm.add_constant(X_ols[anc], has_constant="add")).to_numpy()
        value_model = "OLS hedonic (RQ3: no significant XGBoost advantage)"
    a = df.loc[anc, ["micro_market", "district", "fy", "consideration_inr", "carpet_area_m2", "value_m2"]].copy()
    a["pred_value_m2"] = np.exp(pred_ln)
    a["cf"] = a["pred_value_m2"] / a["value_m2"]
    # record-level factors for external validation (rq4_external_validation.py); no identifiers beyond record_id
    a.assign(record_id=df.loc[anc, "record_id"].to_numpy())[
        ["record_id", "micro_market", "district", "fy", "value_m2", "pred_value_m2", "cf"]
    ].round(4).to_csv(OUT / "rq4_anchored_cf.csv", index=False)

    rows = []
    totals = df.groupby("micro_market").agg(n=("record_id", "size"), district=("district", "first"),
                                            share=("anchored", "mean"))
    for mm, g in a.groupby("micro_market"):
        lo, hi = bootstrap_median_ci(g["cf"].to_numpy())
        rows.append({"micro_market_id": f"{totals.loc[mm, 'district'].lower()}-{mm.lower().replace(' ', '-')}",
                     "micro_market": mm, "district": totals.loc[mm, "district"], "fy": "pooled",
                     "n_transactions": int(totals.loc[mm, "n"]), "n_anchored": len(g),
                     "anchored_share": round(float(totals.loc[mm, "share"]), 4),
                     "cf_median": round(float(g["cf"].median()), 4), "cf_ci_low": round(float(lo), 4),
                     "cf_ci_high": round(float(hi), 4), "reportable": len(g) >= MIN_ANCHORED_FOR_CF,
                     "model_version": MODEL_VERSION, "published_at": date.today().isoformat()})
    cf_tab = pd.DataFrame(rows).sort_values("cf_median", ascending=False)
    # Empirical-Bayes partial pooling of log CF toward the district mean, so thin
    # micro-markets borrow strength (shrinkage weight w = n / (n + sigma2/tau2)).
    a["log_cf"] = np.log(a["cf"])
    sigma2 = a.groupby("micro_market")["log_cf"].var(ddof=1).mean()
    mm_means = a.groupby("micro_market")["log_cf"].mean()
    tau2 = max(float(mm_means.var(ddof=1) - sigma2 / a.groupby("micro_market").size().mean()), 1e-6)
    d_mean = a.groupby("district")["log_cf"].mean()
    eb = []
    for mm, g in a.groupby("micro_market"):
        w = len(g) / (len(g) + sigma2 / tau2)
        eb.append({"micro_market": mm, "eb_weight": round(w, 3),
                   "cf_eb": round(float(np.exp(w * g["log_cf"].mean() + (1 - w) * d_mean[g["district"].iloc[0]])), 4)})
    cf_tab = cf_tab.merge(pd.DataFrame(eb), on="micro_market", how="left")
    # SRO-level factors: coarser unit that usually reaches the reporting threshold sooner
    a["sro_code"] = df.loc[anc, "sro_code"].to_numpy()
    sro_rows = []
    for sro, g in a.groupby("sro_code"):
        lo_, hi_ = bootstrap_median_ci(g["cf"].to_numpy())
        sro_rows.append({"sro_code": sro, "district": g["district"].iloc[0], "n_anchored": len(g),
                         "cf_median": round(float(g["cf"].median()), 4), "cf_ci_low": round(float(lo_), 4),
                         "cf_ci_high": round(float(hi_), 4), "reportable": len(g) >= MIN_ANCHORED_FOR_CF})
    pd.DataFrame(sro_rows).to_csv(OUT / "rq4_cf_by_sro.csv", index=False)
    cf_tab.to_csv(OUT / "correction_factors.csv", index=False)       # Estima upload schema
    seg = []
    for col in ["district", "fy"]:
        for lvl, g in a.groupby(col):
            lo, hi = bootstrap_median_ci(g["cf"].to_numpy())
            seg.append({"segment": col, "level": lvl, "n_anchored": len(g), "cf_median": g["cf"].median(),
                        "cf_ci95_low": lo, "cf_ci95_high": hi})
    lo, hi = bootstrap_median_ci(a["cf"].to_numpy())
    seg.append({"segment": "pooled", "level": "all", "n_anchored": len(a), "cf_median": a["cf"].median(),
                "cf_ci95_low": lo, "cf_ci95_high": hi})
    seg = pd.DataFrame(seg).round(4)
    seg.to_csv(OUT / "rq4_cf_by_segment.csv", index=False)

    residex_note = ("RESIDEX file not present — load it with `python -m src.live.nhb_residex --load <file>`, "
                    "then run `python -m src.pipeline --stage rq4ext`")
    rpath = EXTERNAL_DIR / "residex" / "residex.csv"
    if rpath.exists():
        rx = pd.read_csv(rpath)          # columns: city, quarter, index
        residex_note = f"RESIDEX loaded ({len(rx)} rows); run `python -m src.pipeline --stage rq4ext` for the direction check"

    # ------------------------------------------------------------ figures
    fig, ax = plt.subplots(figsize=(6.2, 5.5))
    for p, nm, col, m in [(p_lg, "Logistic", INK_2, cm_lg), (p_xg, "XGBoost", SERIES[0], cm_xg)]:
        fpr, tpr, _ = roc_curve(y[te], p)
        ax.plot(fpr, tpr, color=col, label=f"{nm} (AUC = {m['AUC']:.3f})")
    ax.plot([0, 1], [0, 1], color="#b9b8b3", ls="--", lw=1, label="Chance (AUC = .50)")
    ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    ax.set_title("RQ4 — ROC on held-out micro-markets"); ax.legend(loc="lower right")
    footer(fig, label); fig.savefig(OUT / "fig_rq4_roc.png"); plt.close(fig)

    o = orr[orr["variable"] != "const"].sort_values("odds_ratio")
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    for i, (_, r) in enumerate(o.iterrows()):
        col = SERIES[0] if r["significant"] else "#b9b8b3"
        ax.plot([r["or_ci95_low"], r["or_ci95_high"]], [i, i], color=col, lw=2)
        ax.plot(r["odds_ratio"], i, "o", color=col, ms=7)
    ax.axvline(1, color=INK_2, lw=1); ax.set_xscale("log")
    ticks = [t for t in [0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4] if o["or_ci95_low"].min() * 0.9 <= t <= o["or_ci95_high"].max() * 1.1]
    ax.set_xticks(ticks, [f"{t:g}" for t in ticks]); ax.minorticks_off()
    ax.set_yticks(range(len(o)), o["term"]); ax.set_xlabel("Odds ratio of anchoring (log scale, 95% CI)")
    ax.set_title("RQ4 — What predicts anchoring? (blue = p < .05)")
    footer(fig, label); fig.savefig(OUT / "fig_rq4_odds_ratios.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 6.5))
    c = cf_tab.sort_values("cf_median")
    cols = [SERIES[0] if r else "#cfcec9" for r in c["reportable"]]
    ax.barh(c["micro_market"], c["cf_median"], color=cols)
    ax.errorbar(c["cf_median"], range(len(c)), xerr=[c["cf_median"] - c["cf_ci_low"], c["cf_ci_high"] - c["cf_median"]],
                fmt="none", ecolor=INK_2, lw=0.8)
    ax.axvline(1, color=INK_2, lw=1)
    ax.set_xlim(left=0.8); ax.tick_params(axis="y", labelsize=7.5)
    ax.set_xlabel("Correction factor = predicted ÷ registered value (median, 95% CI)")
    ax.set_title(f"RQ4 — Micro-market correction factors (blue = reportable, ≥ {MIN_ANCHORED_FOR_CF} anchored)")
    footer(fig, label); fig.savefig(OUT / "fig_rq4_correction_factors.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5))
    for p, nm, col in [(p_lg, "Logistic", INK_2), (p_xg, "XGBoost", SERIES[0])]:
        bins = pd.qcut(p, 8, duplicates="drop")
        cal = pd.DataFrame({"p": p, "y": y[te]}).groupby(bins, observed=True).mean()
        ax.plot(cal["p"], cal["y"], "o-", color=col, label=nm)
    ax.plot([0, 1], [0, 1], color="#b9b8b3", ls="--", lw=1)
    ax.set_xlabel("Predicted probability"); ax.set_ylabel("Observed anchored share")
    ax.set_title("RQ4 — Calibration (held-out)"); ax.legend()
    footer(fig, label); fig.savefig(OUT / "fig_rq4_calibration.png"); plt.close(fig)

    summary = {
        "n": int(len(df)), "events_anchored": n_events, "predictors": k,
        "EPV": round(n_events / k, 1), "EPV_ok_ge_10": bool(n_events / k >= 10),
        "LR_chi2": round(lr_stat, 3), "LR_df": lr_df, "LR_p": float(f"{logit.llr_pvalue:.3g}"),
        "mcfadden_pseudo_R2": round(float(logit.prsquared), 4),
        "decision_alpha_0.05": ("Reject H0: predictors are associated with anchoring" if logit.llr_pvalue < ALPHA
                                else "Fail to reject H0"),
        "significant_predictors_OR": {r["term"]: round(float(r["odds_ratio"]), 3)
                                      for _, r in orr[(orr["variable"] != "const") & orr["significant"]].iterrows()},
        "box_tidwell_violations": bt.loc[~bt["linear_in_logit_ok"], "variable"].tolist(),
        "test_logistic": {k2: (round(v, 4) if isinstance(v, float) else v) for k2, v in cm_lg.items()},
        "test_xgboost": {k2: (round(v, 4) if isinstance(v, float) else v) for k2, v in cm_xg.items()},
        "auc_diff_xgb_minus_logit_ci95": [round(float(auc_diff_ci[0]), 4), round(float(auc_diff_ci[1]), 4)],
        "value_model_for_cf": value_model,
        "cf_pooled_median": round(float(a["cf"].median()), 4),
        "cf_pooled_ci95": [round(float(lo), 4), round(float(hi), 4)],
        "cf_by_district": seg[seg["segment"] == "district"].set_index("level")["cf_median"].round(4).to_dict(),
        "cf_by_fy": seg[seg["segment"] == "fy"].set_index("level")["cf_median"].round(4).to_dict(),
        "micro_markets_total": int(len(cf_tab)),
        "micro_markets_reportable": int(cf_tab["reportable"].sum()),
        "median_anchored_per_micro_market": float(cf_tab["n_anchored"].median()),
        "eb_shrinkage_tau2_sigma2": [round(tau2, 5), round(float(sigma2), 5)],
        "sro_reportable": f"{sum(r['reportable'] for r in sro_rows)} of {len(sro_rows)} SROs",
        "residex_check": residex_note,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=float))
    return summary, sorted(OUT.iterdir())
