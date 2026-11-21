"""
report_figures.py — Redraws every final-report figure from the stage outputs at
print size (6.5 in wide, 11-pt text) so each figure is legible in the Word report.

Run after the pipeline and scripts/final_model_comparison.py:
    python scripts/report_figures.py      -> outputs/report_figures/fig_XX_*.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, RandomizedSearchCV
from xgboost import XGBClassifier

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ANALYSIS_FILE, OUTPUT_DIR, RANDOM_SEED, TEST_GROUP_SHARE  # noqa: E402
from src.models.rq3_gbm_vs_ols import features  # noqa: E402

BLUE, ORANGE, GREEN = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID, MUTED = "#0b0b0b", "#52514e", "#e4e3df", "#b9b7b1"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.titlesize": 12,
                     "axes.labelsize": 11, "xtick.labelsize": 10, "ytick.labelsize": 10,
                     "legend.fontsize": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.edgecolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "legend.frameon": False, "savefig.dpi": 220, "savefig.bbox": "tight"})
OUT = OUTPUT_DIR / "report_figures"
OUT.mkdir(parents=True, exist_ok=True)
W = 6.5


def save(fig, name):
    fig.savefig(OUT / name)
    plt.close(fig)


df = pd.read_csv(ANALYSIS_FILE)

# 1 R distribution
fig, ax = plt.subplots(figsize=(W, 3.6))
r = df.loc[df.r_ratio.between(0.8, 2.6), "r_ratio"]
ax.axvspan(0.98, 1.02, color=ORANGE, alpha=0.18, lw=0)
cnt, edges = np.histogram(r, bins=np.arange(0.8, 2.61, 0.02))
ctr = edges[:-1] + 0.01
ax.bar(ctr, cnt, width=0.018, color=np.where((edges[:-1] >= 0.979) & (edges[:-1] < 1.02), ORANGE, BLUE), lw=0)
ax.annotate("Anchored window\n0.98 ≤ R < 1.02\n(13.4% of sales)", xy=(1.03, 150), xytext=(1.2, 135),
            fontsize=10, color=INK, arrowprops=dict(arrowstyle="->", color=INK2))
ax.set_xlabel("R = registered consideration ÷ ASR value")
ax.set_ylabel("Number of sales")
save(fig, "fig01_r_distribution.png")

# 2 value vs ASR
fig, ax = plt.subplots(figsize=(W, 4.2))
for d, c in [("Pune", BLUE), ("Thane", ORANGE)]:
    s = df[df.district == d]
    ax.scatter(s.asr_rate_m2 / 1000, s.value_m2 / 1000, s=10, alpha=0.55, color=c, label=d, lw=0)
lim = [df.asr_rate_m2.min() / 1000 * 0.9, df.value_m2.max() / 1000 * 1.05]
ax.plot(lim, lim, ls="--", color=INK2, lw=1.2, label="Value = ASR rate")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("ASR rate (₹ thousand per m², log scale)")
ax.set_ylabel("Registered value (₹ thousand per m², log scale)")
ax.legend(loc="upper left", markerscale=2)
save(fig, "fig02_value_vs_asr.png")

# 3 correlation heatmap (core variables)
cols = {"ln_value_m2": "ln value/m²", "ln_asr_rate_m2": "ln ASR rate", "ln_carpet_area": "ln area",
        "floor_no": "Floor", "new_sale": "New sale", "parking": "Parking", "dist_rail_km": "Dist. station",
        "dist_cbd_km": "Dist. CBD", "municipal_corp": "Municipal", "anchored": "Anchored"}
c = df[list(cols)].corr().rename(index=cols, columns=cols)
fig, ax = plt.subplots(figsize=(W, 5.4))
ax.grid(False)
from matplotlib.colors import LinearSegmentedColormap
cmap = LinearSegmentedColormap.from_list("div", ["#e34948", "#f0efec", BLUE])
im = ax.imshow(c, cmap=cmap, vmin=-1, vmax=1)
ax.set_xticks(range(len(c))); ax.set_xticklabels(c.columns, rotation=45, ha="right")
ax.set_yticks(range(len(c))); ax.set_yticklabels(c.index)
for i in range(len(c)):
    for j in range(len(c)):
        v = c.iloc[i, j]
        ax.text(j, i, f"{v:.2f}".replace("0.", ".").replace("-.", "−."), ha="center", va="center",
                fontsize=8.5, color="white" if abs(v) > 0.6 else INK)
fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02, label="Pearson r")
save(fig, "fig03_correlation.png")

# 4 architecture diagram
fig, ax = plt.subplots(figsize=(W, 4.6))
ax.set_xlim(0, 100); ax.set_ylim(0, 72); ax.axis("off")
stages = [("1  Ingestion", "Index-II, ASR, MahaRERA,\nOSM, RESIDEX, RBI"),
          ("2  Preprocessing", "Translation, DPDP masking,\nfilters, exclusion log"),
          ("3  EDA", "Distributions, R spike,\ncorrelations, outliers"),
          ("4  Features", "Logs, area basis,\ndistances, dummies"),
          ("5  Modeling", "RQ1 bunching, RQ2 OLS,\nRQ3 ML vs OLS, RQ4 logit"),
          ("6  Evaluation", "Grouped hold-out, MAE,\nAUC, paired tests"),
          ("7  Deployment", "FastAPI scoring service\n→ Estima Fair Value Score")]
colors = [BLUE, BLUE, GREEN, GREEN, ORANGE, ORANGE, INK2]
pos = [(2, 44), (35, 44), (68, 44), (68, 14), (35, 14), (2, 14)]
pos = [(1, 46), (34.5, 46), (68, 46), (68, 16), (34.5, 16), (1, 16), None]
for k, ((t, sub), col, p) in enumerate(zip(stages[:6], colors, pos)):
    x, y = p
    ax.add_patch(FancyBboxPatch((x, y), 31, 20, boxstyle="round,pad=0.4,rounding_size=1.5",
                                fc="white", ec=col, lw=2))
    ax.text(x + 15.5, y + 14.5, t, ha="center", va="center", fontsize=8.6, weight="bold", color=INK)
    ax.text(x + 15.5, y + 6.5, sub, ha="center", va="center", fontsize=7.6, color=INK2)
arrow = dict(arrowstyle="-|>", color=INK2, lw=1.5, mutation_scale=14)
ax.annotate("", (34.3, 56), (32.4, 56), arrowprops=arrow)
ax.annotate("", (67.8, 56), (65.9, 56), arrowprops=arrow)
ax.annotate("", (83.5, 36.6), (83.5, 45.6), arrowprops=arrow)
ax.annotate("", (65.9, 26), (67.8, 26), arrowprops=arrow)
ax.annotate("", (32.4, 26), (34.3, 26), arrowprops=arrow)
ax.add_patch(FancyBboxPatch((1, 1), 98, 9, boxstyle="round,pad=0.4,rounding_size=1.5", fc="#f3f2ee", ec=INK2, lw=1.5))
ax.text(50, 5.5, "7  Deployment: FastAPI scoring service → Estima Fair Value Score + LLM explanation",
        ha="center", va="center", fontsize=8.6, weight="bold", color=INK)
ax.annotate("", (16.5, 10.6), (16.5, 15.6), arrowprops=arrow)
ax.text(50, 69, "Storage zones: data/raw → data/interim → data/processed → outputs/<stage>   ·   quality gate between stages",
        ha="center", fontsize=7.8, color=INK2, style="italic")
save(fig, "fig04_architecture.png")

# 5 train vs test MAE
comp = pd.read_csv(OUTPUT_DIR / "final" / "value_model_comparison.csv")
fig, ax = plt.subplots(figsize=(W, 3.6))
x = np.arange(len(comp)); w = 0.36
b1 = ax.bar(x - w / 2 - 0.01, comp.train_MAE, w, color=MUTED, label="Training micro-markets")
b2 = ax.bar(x + w / 2 + 0.01, comp.test_MAE, w, color=BLUE, label="Held-out micro-markets")
for b in list(b1) + list(b2):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.002, f"{b.get_height():.3f}",
            ha="center", va="bottom", fontsize=9.5, color=INK)
ax.set_xticks(x); ax.set_xticklabels(comp.model)
ax.set_ylabel("MAE (log points)"); ax.set_ylim(0, 0.145)
ax.legend(loc="upper left", ncol=2)
save(fig, "fig05_train_test_mae.png")

# 6 predicted vs actual
p = pd.read_csv(OUTPUT_DIR / "rq3" / "rq3_test_predictions.csv")
fig, axes = plt.subplots(1, 2, figsize=(W, 3.4), sharey=True)
lo, hi = p[["y", "pred_ols", "pred_xgb"]].min().min() - 0.05, p[["y", "pred_ols", "pred_xgb"]].max().max() + 0.05
for ax, col, name, cc in [(axes[0], "pred_ols", "OLS hedonic", BLUE), (axes[1], "pred_xgb", "XGBoost", ORANGE)]:
    ax.scatter(p.y, p[col], s=10, alpha=0.6, color=cc, lw=0)
    ax.plot([lo, hi], [lo, hi], ls="--", color=INK2, lw=1.1)
    ax.set_title(name, loc="left")
    ax.set_xlabel("Actual ln value per m²")
axes[0].set_ylabel("Predicted ln value per m²")
save(fig, "fig06_pred_vs_actual.png")

# 7 ROC curves (logit from final script; XGB classifier refit exactly as in rq4 stage)
X_ols, X_xgb = features(df)
from src.models.rq2_hedonic import design
y, g = df.anchored.to_numpy(), df.micro_market.to_numpy()
tr, te = next(GroupShuffleSplit(1, test_size=TEST_GROUP_SHARE, random_state=RANDOM_SEED).split(X_ols, y, g))
search = RandomizedSearchCV(
    XGBClassifier(objective="binary:logistic", eval_metric="logloss", random_state=RANDOM_SEED, n_jobs=4, tree_method="hist"),
    {"max_depth": [2, 3, 4, 5], "learning_rate": [0.03, 0.05, 0.1], "n_estimators": [200, 400],
     "min_child_weight": [1, 5, 10], "subsample": [0.8, 1.0], "colsample_bytree": [0.8, 1.0]},
    n_iter=20, scoring="roc_auc", cv=GroupKFold(n_splits=5), random_state=RANDOM_SEED, n_jobs=1)
search.fit(X_xgb.iloc[tr], y[tr], groups=g[tr])
p_xg = search.best_estimator_.predict_proba(X_xgb.iloc[te])[:, 1]
sc = pd.read_csv(OUTPUT_DIR / "final" / "classifier_test_scores.csv")
fig, ax = plt.subplots(figsize=(W * 0.72, 4.0))
for yy, pp, name, cc in [(sc.y, sc.p_logit, "Logistic regression", BLUE), (y[te], p_xg, "XGBoost classifier", ORANGE)]:
    fpr, tpr, _ = roc_curve(yy, pp)
    ax.plot(fpr, tpr, color=cc, lw=2, label=f"{name} (AUC = {roc_auc_score(yy, pp):.3f})")
ax.plot([0, 1], [0, 1], ls="--", color=INK2, lw=1, label="Chance (AUC = .500)")
ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
ax.legend(loc="lower right")
save(fig, "fig07_roc.png")

# 8 confusion matrices with anchored / not anchored labels
fig, axes = plt.subplots(1, 2, figsize=(W, 3.3), gridspec_kw={"wspace": 0.12})
for ax, part, title in [(axes[0], "train", "Training (n = 1,306)"), (axes[1], "test", "Test (n = 404)")]:
    cm = pd.read_csv(OUTPUT_DIR / "final" / f"confusion_logit_{part}.csv", index_col=0).to_numpy()
    ax.grid(False)
    shade = np.array([[BLUE, "#f3c8b6"], ["#f3c8b6", BLUE]])
    for i in range(2):
        for j in range(2):
            correct = i == j
            ax.add_patch(plt.Rectangle((j, 1 - i), 1, 1, fc=BLUE if correct else "#fbe3d8", ec="white", lw=3))
            lab = [["TP", "FN"], ["FP", "TN"]][i][j]
            ax.text(j + 0.5, 1 - i + 0.58, f"{cm[i, j]:,}", ha="center", va="center", fontsize=15, weight="bold",
                    color="white" if correct else INK)
            ax.text(j + 0.5, 1 - i + 0.28, lab, ha="center", va="center", fontsize=10, color="white" if correct else INK2)
    ax.set_xlim(0, 2); ax.set_ylim(0, 2)
    ax.set_xticks([0.5, 1.5]); ax.set_xticklabels(["Anchored", "Not anchored"])
    ax.set_yticks([1.5, 0.5]); ax.set_yticklabels(["Anchored", "Not\nanchored"])
    ax.set_xlabel("Predicted class"); ax.set_title(title, loc="left")
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
axes[1].set_yticklabels([])
axes[0].set_ylabel("Actual class")
save(fig, "fig08_confusion.png")

# 9 bunching
bins = pd.read_csv(OUTPUT_DIR / "rq1" / "rq1_bins.csv")
b = bins[bins.bin_left.between(0.8, 2.0)]
fig, ax = plt.subplots(figsize=(W, 3.6))
ax.bar(b.bin_left + 0.005, b.observed, width=0.009, color=np.where(b.in_window, ORANGE, BLUE), lw=0)
ax.plot(b.bin_left + 0.005, b.counterfactual.clip(lower=0), color=INK, lw=1.8, label="Counterfactual density (7th-degree polynomial)")
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
ax.set_xlabel("R = registered consideration ÷ ASR value"); ax.set_ylabel("Sales per bin")
ax.legend(handles=[Patch(color=BLUE, label="Observed sales per 0.01 bin"),
                   Patch(color=ORANGE, label="Observed, anchored window (±2%)"),
                   Line2D([], [], color=INK, lw=1.8, label="Counterfactual (7th-degree polynomial)")], loc="upper right")
save(fig, "fig09_bunching.png")

# 10 standardized coefficients
co = pd.read_csv(OUTPUT_DIR / "rq2" / "rq2_coefficients_full.csv").dropna(subset=["std_beta"])
co = co[co.variable != "ln_asr_rate_m2"].sort_values("std_beta")
fig, ax = plt.subplots(figsize=(W, 4.0))
ax.barh(co.term, co.std_beta, color=np.where(co.significant_hc3, BLUE, MUTED), height=0.62)
ax.axvline(0, color=INK2, lw=1)
ax.set_xlabel("Standardized coefficient (β)")
asr = pd.read_csv(OUTPUT_DIR / "rq2" / "rq2_coefficients_full.csv").query("variable=='ln_asr_rate_m2'").std_beta.iloc[0]
ax.text(0.98, 0.04, f"ln ASR rate β = {asr:.2f} (omitted from scale)\nBlue = significant at p < .05 (HC3)",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=9, color=INK2)
save(fig, "fig10_std_coefficients.png")

# 11 feature importance: SHAP + permutation
shap_all = pd.read_csv(OUTPUT_DIR / "rq3" / "rq3_shap_importance.csv")
asr_shap = shap_all.iloc[0].mean_abs_shap
shap = shap_all.iloc[1:8].iloc[::-1]
perm = pd.read_csv(OUTPUT_DIR / "final" / "permutation_importance.csv")
po_all = perm[perm.model == "OLS"].sort_values("mae_increase", ascending=False)
asr_perm = po_all.iloc[0].mae_increase
po = po_all.iloc[1:8].iloc[::-1]
fig, axes = plt.subplots(1, 2, figsize=(W, 3.9))
axes[0].barh(shap.feature, shap.mean_abs_shap, color=ORANGE, height=0.6)
axes[0].set_title("XGBoost: mean |SHAP|", loc="left")
axes[0].set_xlabel(f"log points (ln ASR rate = {asr_shap:.3f})", fontsize=9.5)
axes[1].barh(po.label, po.mae_increase.clip(lower=0), color=BLUE, height=0.6)
axes[1].set_title("OLS: permutation importance", loc="left")
axes[1].set_xlabel(f"Test MAE increase (ln ASR rate = {asr_perm:.3f})", fontsize=9.5)
for ax in axes:
    ax.tick_params(axis="y", labelsize=8.5)
fig.tight_layout(w_pad=1.5)
save(fig, "fig11_feature_importance.png")

# 12 correction factors by SRO
s = pd.read_csv(OUTPUT_DIR / "rq4" / "rq4_cf_by_sro.csv").sort_values("cf_median")
fig, ax = plt.subplots(figsize=(W, 3.8))
col = np.where(s.reportable, BLUE, MUTED)
ax.errorbar(s.cf_median, range(len(s)), xerr=[s.cf_median - s.cf_ci_low, s.cf_ci_high - s.cf_median],
            fmt="none", ecolor=INK2, lw=1.2, capsize=3)
ax.scatter(s.cf_median, range(len(s)), color=col, s=60, zorder=3, edgecolor="white", lw=1.5)
ax.set_yticks(range(len(s)))
ax.set_yticklabels([f"{a} ({d}, n = {n})" for a, d, n in zip(s.sro_code, s.district, s.n_anchored)], fontsize=9)
pooled = json.loads((OUTPUT_DIR / "rq4" / "summary.json").read_text())["cf_pooled_median"]
ax.axvline(pooled, ls="--", color=ORANGE, lw=1.4)
ax.text(pooled + 0.005, len(s) - 0.6, f"Pooled = {pooled:.2f}", color=INK, fontsize=9.5)
ax.axvline(1, color=INK2, lw=1)
ax.set_xlabel("Correction factor (median predicted ÷ registered value), 95% CI")
save(fig, "fig12_correction_factors.png")
print("figures written to", OUT)
