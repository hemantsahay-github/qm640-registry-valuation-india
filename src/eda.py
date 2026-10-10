"""
eda.py — Stage 2: Exploratory Data Analysis on the analysis dataset.

Produces (outputs/eda/):
  01_dataset_info.txt         shape, dtypes, memory (df.info)
  02_null_values.csv          null count and % per column (after cleaning)
  02b_null_values_before_cleaning.csv  missingness in the masked interim data
  03_descriptive_stats.csv    count, mean, median, std, min, quartiles, max, skew, kurtosis
  04_category_counts.csv      frequency of every categorical level
  05_group_means.csv          mean / median value per m2 and anchored share by district x FY
  06_correlation_pearson.csv  and 06_correlation_spearman.csv
  07_outliers_iqr.csv         IQR outlier counts per numeric column
  fig_*.png                   histograms, boxplots, heatmap, scatter, counts, R-ratio density
"""
from __future__ import annotations

import io

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import ANALYSIS_FILE, ANCHOR_HI, ANCHOR_LO, INTERIM_FILE, OUTPUT_DIR
from matplotlib.ticker import FuncFormatter

from src.utils.plotstyle import DISTRICT_COLOR, DIVERGING, INK_2, SERIES, footer

OUT = OUTPUT_DIR / "eda"
NUMERIC = ["consideration_inr", "asr_value_inr", "stamp_duty_inr", "carpet_area_m2",
           "floor_no", "dist_rail_km", "dist_cbd_km", "asr_rate_m2", "value_m2", "r_ratio"]
BINARY = ["area_basis", "new_sale", "parking", "municipal_corp", "anchored"]
CATEGORICAL = ["district", "fy", "doc_type", "sro_code", "micro_market"]
LABELS = {"consideration_inr": "Consideration (₹)", "asr_value_inr": "ASR value (₹)",
          "stamp_duty_inr": "Stamp duty (₹)", "carpet_area_m2": "Carpet area (m²)",
          "floor_no": "Floor", "dist_rail_km": "Dist. to station (km)",
          "dist_cbd_km": "Dist. to CBD (km)", "asr_rate_m2": "ASR rate (₹/m²)",
          "value_m2": "Value (₹/m²)", "r_ratio": "R = consideration / ASR value"}


def _short(x, _pos=None) -> str:
    """Compact rupee ticks: 1.2 Cr, 85 L, 95k."""
    if abs(x) >= 1e7:
        return f"{x / 1e7:.1f} Cr"
    if abs(x) >= 1e5:
        return f"{x / 1e5:.0f} L"
    return f"{x / 1e3:.0f}k"


def run(label: str) -> tuple[dict, list]:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(ANALYSIS_FILE, parse_dates=["reg_date"])
    files = []

    buf = io.StringIO()
    df.info(buf=buf)
    (OUT / "01_dataset_info.txt").write_text(f"{label}\n\nShape: {df.shape}\n\n{buf.getvalue()}")
    nulls = pd.DataFrame({"null_count": df.isna().sum(), "null_pct": (df.isna().mean() * 100).round(2)})
    nulls.to_csv(OUT / "02_null_values.csv")
    # missingness BEFORE exclusions (the analysis file is complete by construction)
    pre = pd.read_csv(INTERIM_FILE)
    pre_nulls = pd.DataFrame({"null_count": pre.isna().sum(), "null_pct": (pre.isna().mean() * 100).round(2)})
    pre_nulls.to_csv(OUT / "02b_null_values_before_cleaning.csv")

    num = df[NUMERIC + BINARY]
    desc = num.describe().T
    desc.insert(2, "median", num.median())
    desc["skew"], desc["kurtosis"] = num.skew(), num.kurtosis()
    desc.round(3).to_csv(OUT / "03_descriptive_stats.csv")

    counts = pd.concat([df[c].value_counts().rename("count").to_frame().assign(variable=c)
                        for c in CATEGORICAL + BINARY])
    counts.to_csv(OUT / "04_category_counts.csv")

    grp = df.groupby(["district", "fy"]).agg(
        n=("record_id", "size"), mean_value_m2=("value_m2", "mean"),
        median_value_m2=("value_m2", "median"), median_asr_m2=("asr_rate_m2", "median"),
        median_r=("r_ratio", "median"), anchored_share=("anchored", "mean")).round(3)
    grp.to_csv(OUT / "05_group_means.csv")

    corr_cols = ["ln_value_m2", "ln_asr_rate_m2", "ln_carpet_area", "floor_no", "new_sale",
                 "parking", "area_basis", "dist_rail_km", "dist_cbd_km", "municipal_corp",
                 "r_ratio", "anchored"]
    pear = df[corr_cols].corr().round(3)
    pear.to_csv(OUT / "06_correlation_pearson.csv")
    df[corr_cols].corr(method="spearman").round(3).to_csv(OUT / "06_correlation_spearman.csv")

    q1, q3 = df[NUMERIC].quantile(0.25), df[NUMERIC].quantile(0.75)
    iqr = q3 - q1
    out_n = ((df[NUMERIC] < q1 - 1.5 * iqr) | (df[NUMERIC] > q3 + 1.5 * iqr)).sum()
    out_n.rename("iqr_outliers").to_csv(OUT / "07_outliers_iqr.csv")

    # ---------------- figures
    fig, axes = plt.subplots(2, 5, figsize=(16, 6.2))
    for ax, c in zip(axes.flat, NUMERIC):
        for d, g in df.groupby("district"):
            ax.hist(g[c].dropna(), bins=30, alpha=0.55, color=DISTRICT_COLOR[d], label=d)
        ax.set_title(LABELS[c], fontsize=9.5)
        if df[c].max() > 10000:
            ax.xaxis.set_major_formatter(FuncFormatter(_short))
    axes.flat[0].legend()
    fig.suptitle("Distribution of numeric variables by district", fontweight="bold")
    fig.tight_layout(); footer(fig, label); fig.savefig(OUT / "fig_01_histograms.png"); plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, c in zip(axes, ["value_m2", "asr_rate_m2", "r_ratio"]):
        data = [g[c].dropna() for _, g in df.groupby("district")]
        bp = ax.boxplot(data, tick_labels=sorted(df["district"].unique()), patch_artist=True, widths=0.5)
        for patch, col in zip(bp["boxes"], SERIES):
            patch.set_facecolor(col); patch.set_alpha(0.6)
        ax.set_title(LABELS[c])
    fig.suptitle("Boxplots by district (outliers shown as points)", fontweight="bold")
    fig.tight_layout(); footer(fig, label); fig.savefig(OUT / "fig_02_boxplots.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 7.5))
    im = ax.imshow(pear, cmap=DIVERGING, vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr_cols)), corr_cols, rotation=60, ha="right")
    ax.set_yticks(range(len(corr_cols)), corr_cols); ax.grid(False)
    for i in range(len(corr_cols)):
        for j in range(len(corr_cols)):
            ax.text(j, i, f"{pear.iloc[i, j]:.2f}", ha="center", va="center", fontsize=7,
                    color="#0b0b0b")
    fig.colorbar(im, shrink=0.75, label="Pearson r")
    ax.set_title("Correlation matrix of analysis variables")
    footer(fig, label); fig.savefig(OUT / "fig_03_correlation_heatmap.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5.5))
    for d, g in df.groupby("district"):
        ax.scatter(g["ln_asr_rate_m2"], g["ln_value_m2"], s=10, alpha=0.45, color=DISTRICT_COLOR[d], label=d)
    lo, hi = df["ln_asr_rate_m2"].min(), df["ln_asr_rate_m2"].max()
    ax.plot([lo, hi], [lo, hi], color=INK_2, lw=1.2, ls="--", label="Value = ASR rate")
    ax.set_xlabel("ln ASR rate (₹/m²)"); ax.set_ylabel("ln registered value (₹/m²)")
    ax.set_title("Registered value against ASR rate"); ax.legend()
    footer(fig, label); fig.savefig(OUT / "fig_04_value_vs_asr.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    bins = np.arange(0.80, 2.001, 0.01)
    ax.hist(df["r_ratio"][df["r_ratio"].between(0.80, 2.0)], bins=bins, color=SERIES[0], alpha=0.85)
    ax.axvspan(ANCHOR_LO, ANCHOR_HI, color=SERIES[1], alpha=0.25, label="Anchoring window 0.98–1.02")
    ax.set_xlabel("R = consideration / ASR value (bin width 0.01)"); ax.set_ylabel("Transactions")
    ax.set_title("Distribution of R: visible spike at the ASR threshold?"); ax.legend()
    footer(fig, label); fig.savefig(OUT / "fig_05_r_ratio_distribution.png"); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))
    cnt = df.groupby(["fy", "district"]).size().unstack()
    cnt.plot(kind="bar", ax=axes[0], color=[DISTRICT_COLOR[c] for c in cnt.columns], rot=0, width=0.7)
    axes[0].set_title("Transactions by financial year and district"); axes[0].set_xlabel("")
    top = df["micro_market"].value_counts().head(15)[::-1]
    axes[1].barh(top.index, top.values, color=SERIES[0])
    axes[1].set_title("Top 15 micro-markets by record count")
    fig.tight_layout(); footer(fig, label); fig.savefig(OUT / "fig_06_counts.png"); plt.close(fig)

    files = sorted(OUT.iterdir())
    summary = {
        "rows": int(df.shape[0]), "columns": int(df.shape[1]),
        "meets_min_N_1068": bool(len(df) >= 1068),
        "total_nulls_after_cleaning": int(df.isna().sum().sum()),
        "nulls_before_cleaning": pre_nulls.query("null_count > 0")["null_count"].to_dict(),
        "columns_with_nulls": nulls.query("null_count > 0").index.tolist(),
        "records_by_district": df["district"].value_counts().to_dict(),
        "records_by_fy": df["fy"].value_counts().sort_index().to_dict(),
        "mean_value_m2": round(df["value_m2"].mean()), "median_value_m2": round(df["value_m2"].median()),
        "median_r_ratio": round(df["r_ratio"].median(), 4),
        "anchored_share": round(df["anchored"].mean(), 4),
        "corr_ln_value_ln_asr": float(pear.loc["ln_value_m2", "ln_asr_rate_m2"]),
        "top_abs_corr_with_ln_value": pear["ln_value_m2"].drop(["ln_value_m2", "r_ratio"]).abs()
                                         .sort_values(ascending=False).head(4).round(3).to_dict(),
        "iqr_outliers": out_n.to_dict(),
    }
    return summary, files
