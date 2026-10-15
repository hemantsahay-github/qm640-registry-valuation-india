"""
rq4_external_validation.py — RQ4 (live data): does the correction factor move
in the direction that independent market indices imply?

Inputs  : outputs/rq4/rq4_anchored_cf.csv           (from rq4_anchoring.py)
          data/processed/analysis_dataset.csv        (ASR rates by district x FY)
          data/external/rbi_dbie/rbi_hpi.csv         (src.live.rbi_hpi)       and/or
          data/external/residex/residex.csv          (src.live.nhb_residex)
Logic   : For each district x FY
            CF_med        median correction factor of anchored deals
            index_yoy     growth of the market index (mean of quarters in the FY)
            asr_yoy       growth of the median ASR rate per m2 in the registry
            gap           index_yoy - asr_yoy  (market outpacing the circle rate)
            cf_change     change in CF_med from the previous FY
          If registered values anchor to an ASR that lags the market, CF should
          rise when gap > 0. Reported: direction agreement share, Spearman rho
          between gap and cf_change, and a comparison table/figure per index.
Note    : With 2 districts x 3 FYs there are only 4 year-on-year comparisons, so
          this is a direction (face-validity) check, not a significance test.
Outputs : outputs/rq4/external/*.csv, *.png, summary.json
"""
from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src.config import ANALYSIS_FILE, EXTERNAL_DIR, OUTPUT_DIR
from src.utils.plotstyle import DISTRICT_COLOR, INK_2, footer

OUT = OUTPUT_DIR / "rq4" / "external"
INDEX_FILES = {"RBI HPI": EXTERNAL_DIR / "rbi_dbie" / "rbi_hpi.csv",
               "NHB RESIDEX": EXTERNAL_DIR / "residex" / "residex.csv"}


def fy_of_quarter(q: str) -> str:
    """'FY26Q1' -> '2025-26'."""
    end = 2000 + int(q[2:4])
    return f"{end - 1}-{str(end)[-2:]}"


def compare(cf: pd.DataFrame, analysis: pd.DataFrame, index: pd.DataFrame) -> pd.DataFrame:
    cfm = cf.groupby(["district", "fy"])["cf"].median().rename("cf_median")
    asr = analysis.groupby(["district", "fy"])["asr_rate_m2"].median().rename("asr_rate_median")
    idx = index.assign(fy=index["quarter"].map(fy_of_quarter)).rename(columns={"city": "district"})
    idx = idx.groupby(["district", "fy"])["index"].mean().rename("index_mean")
    t = pd.concat([cfm, asr, idx], axis=1).reset_index().sort_values(["district", "fy"])
    g = t.groupby("district")
    t["index_yoy"] = g["index_mean"].pct_change()
    t["asr_yoy"] = g["asr_rate_median"].pct_change()
    t["gap"] = t["index_yoy"] - t["asr_yoy"]
    t["cf_change"] = g["cf_median"].diff()
    t["direction_agree"] = np.where(t["gap"].notna() & t["cf_change"].notna(),
                                    np.sign(t["gap"]) == np.sign(t["cf_change"]), np.nan)
    return t


def run(label: str) -> tuple[dict, list]:
    OUT.mkdir(parents=True, exist_ok=True)
    cf_path = OUTPUT_DIR / "rq4" / "rq4_anchored_cf.csv"
    available = {k: p for k, p in INDEX_FILES.items() if p.exists()}
    if not cf_path.exists() or not available:
        summary = {"status": "SKIPPED",
                   "reason": ("run --stage rq4 first" if not cf_path.exists() else
                              "no index file: load RBI HPI (python -m src.live.rbi_hpi --load <file>) "
                              "or RESIDEX (python -m src.live.nhb_residex --load <file>)")}
        (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
        return summary, [OUT / "summary.json"]

    cf, analysis = pd.read_csv(cf_path), pd.read_csv(ANALYSIS_FILE)
    summary, files = {"status": "OK", "indices": {}}, []
    fig, axes = plt.subplots(1, len(available), figsize=(6.5 * len(available), 4.5), squeeze=False)
    for ax, (name, path) in zip(axes[0], available.items()):
        t = compare(cf, analysis, pd.read_csv(path))
        f = OUT / f"cf_vs_{name.replace(' ', '_').lower()}.csv"
        t.round(4).to_csv(f, index=False); files.append(f)
        valid = t.dropna(subset=["gap", "cf_change"])
        rho = stats.spearmanr(valid["gap"], valid["cf_change"]).statistic if len(valid) >= 3 else None
        summary["indices"][name] = {
            "comparisons": int(len(valid)),
            "direction_agreement_share": round(float(valid["direction_agree"].mean()), 3) if len(valid) else None,
            "spearman_gap_vs_cf_change": None if rho is None or np.isnan(rho) else round(float(rho), 3),
            "index_yoy_by_district_fy": {f"{d} {y}": round(float(v), 4) for d, y, v in
                                         t.dropna(subset=["index_yoy"])[["district", "fy", "index_yoy"]]
                                         .itertuples(index=False)},
        }
        for d, g in t.groupby("district"):
            ax.plot(g["fy"], g["cf_median"], "o-", color=DISTRICT_COLOR.get(d, INK_2), label=f"{d} CF")
        ax.set_title(f"Correction factor by FY — compare with {name}")
        ax.set_ylabel("Median correction factor"); ax.legend()
        txt = "\n".join(f"{k}: index YoY {v:+.1%}" for k, v in summary["indices"][name]["index_yoy_by_district_fy"].items())
        ax.text(0.02, 0.02, txt or "index YoY: n/a", transform=ax.transAxes, fontsize=8, color=INK_2, va="bottom")
    fig.tight_layout(); footer(fig, label)
    fp = OUT / "fig_rq4_cf_vs_indices.png"; fig.savefig(fp); plt.close(fig); files.append(fp)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2)); files.append(OUT / "summary.json")
    return summary, files
