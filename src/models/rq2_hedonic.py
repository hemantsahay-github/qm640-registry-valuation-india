"""
rq2_hedonic.py — RQ2: Which property and locational attributes significantly
explain ln(registered consideration per m2) beyond the ASR rate alone?

Method  : Hedonic OLS (Rosen, 1974), restricted vs. full model.
  Restricted : ln_value_m2 ~ ln_asr_rate_m2                         (k = 1)
  Full       : + 11 attributes (u = 11, k = 12 predictors in total)
  1. Partial F test of the R^2 increase (Equation 2):  H0: dR^2 = 0.
     Also a robust Wald test of the same 11 restrictions with HC3 covariance.
  2. Coefficients with HC3 standard errors (Long & Ervin, 2000); sensitivity
     with standard errors clustered by micro-market.
  3. ASR elasticity test H0: beta_ASR = 1 (an elasticity near 1 with little
     added R^2 would itself signal anchoring).
  4. Diagnostics: VIF (< 5 target), Breusch-Pagan, Jarque-Bera, Durbin-Watson,
     condition number, residual-vs-fitted plot, Q-Q plot.
  5. Effect sizes: % effect = 100 x (exp(b) - 1) for dummies; standardized betas
     to rank attributes.
Outputs : outputs/rq2/*.csv, *.png, summary.json
"""
from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson, jarque_bera

from src.config import ALPHA, ANALYSIS_FILE, OUTPUT_DIR
from src.utils.plotstyle import INK_2, SERIES, footer

OUT = OUTPUT_DIR / "rq2"
Y = "ln_value_m2"
BASE = ["ln_asr_rate_m2"]
ATTRS = ["ln_carpet_area", "area_basis", "floor_no", "new_sale", "parking",
         "dist_rail_km", "dist_cbd_km", "district_Thane", "municipal_corp",
         "fy_2024_25", "fy_2025_26"]
LABELS = {"const": "Intercept", "ln_asr_rate_m2": "ln ASR rate (₹/m²)",
          "ln_carpet_area": "ln carpet area (m²)", "area_basis": "Carpet area recorded directly",
          "floor_no": "Floor (per floor)", "new_sale": "New sale (promoter)", "parking": "Parking included",
          "dist_rail_km": "Distance to station (km)", "dist_cbd_km": "Distance to CBD (km)",
          "district_Thane": "Thane (vs. Pune)", "municipal_corp": "Municipal corporation",
          "fy_2024_25": "FY 2024–25 (vs. 2023–24)", "fy_2025_26": "FY 2025–26 (vs. 2023–24)"}


def design(df: pd.DataFrame) -> pd.DataFrame:
    X = df[["ln_asr_rate_m2", "ln_carpet_area", "area_basis", "floor_no", "new_sale", "parking",
            "dist_rail_km", "dist_cbd_km", "municipal_corp"]].astype(float).copy()
    X["district_Thane"] = (df["district"] == "Thane").astype(float)
    X["fy_2024_25"] = (df["fy"] == "2024-25").astype(float)
    X["fy_2025_26"] = (df["fy"] == "2025-26").astype(float)
    return X[BASE + ATTRS]


def run(label: str) -> tuple[dict, list]:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(ANALYSIS_FILE)
    X, y = design(df), df[Y]
    n, k, u = len(df), len(BASE + ATTRS), len(ATTRS)

    restricted = sm.OLS(y, sm.add_constant(X[BASE])).fit()
    full = sm.OLS(y, sm.add_constant(X)).fit()
    full_hc3 = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HC3")
    full_cl = sm.OLS(y, sm.add_constant(X)).fit(cov_type="cluster",
                                                 cov_kwds={"groups": df["micro_market"].astype("category").cat.codes})

    # 1. partial F test (Equation 2) and robust Wald equivalent
    r2f, r2r = full.rsquared, restricted.rsquared
    F = ((r2f - r2r) / u) / ((1 - r2f) / (n - k - 1))
    p_F = stats.f.sf(F, u, n - k - 1)
    f2 = (r2f - r2r) / (1 - r2f)                        # Cohen's f^2 for the increment
    wald = full_hc3.f_test(", ".join(f"{a} = 0" for a in ATTRS))   # HC3-robust Wald F

    # 2. coefficient table
    ci = full_hc3.conf_int(alpha=ALPHA)
    coef = pd.DataFrame({
        "term": [LABELS[t] for t in full_hc3.params.index], "variable": full_hc3.params.index,
        "b": full_hc3.params, "se_hc3": full_hc3.bse, "t_hc3": full_hc3.tvalues, "p_hc3": full_hc3.pvalues,
        "ci95_low": ci[0], "ci95_high": ci[1], "se_cluster": full_cl.bse, "p_cluster": full_cl.pvalues})
    sd_x = X.std(); sd_y = y.std()
    coef["std_beta"] = [np.nan if v == "const" else full.params[v] * sd_x[v] / sd_y for v in coef["variable"]]
    coef["pct_effect"] = [np.nan if v in ("const", "ln_asr_rate_m2", "ln_carpet_area")
                          else 100 * (np.exp(b) - 1) for v, b in zip(coef["variable"], coef["b"])]
    coef["significant_hc3"] = coef["p_hc3"] < ALPHA
    coef["significant_cluster"] = coef["p_cluster"] < ALPHA
    coef.round(5).to_csv(OUT / "rq2_coefficients_full.csv", index=False)
    pd.DataFrame({"term": restricted.params.index, "b": restricted.params,
                  "se": restricted.HC3_se, "p": restricted.pvalues}).round(5).to_csv(
        OUT / "rq2_coefficients_restricted.csv", index=False)

    # 3. ASR elasticity H0: beta = 1
    b_asr, se_asr = full_hc3.params["ln_asr_rate_m2"], full_hc3.bse["ln_asr_rate_m2"]
    t_asr1 = (b_asr - 1) / se_asr
    p_asr1 = 2 * stats.norm.sf(abs(t_asr1))

    # 4. diagnostics
    vif = pd.DataFrame({"variable": X.columns,
                        "vif": [variance_inflation_factor(sm.add_constant(X).values, i + 1)
                                for i in range(X.shape[1])]}).round(3)
    vif.to_csv(OUT / "rq2_vif.csv", index=False)
    bp_stat, bp_p, _, _ = het_breuschpagan(full.resid, full.model.exog)
    jb_stat, jb_p, skew, kurt = jarque_bera(full.resid)
    diag = {"breusch_pagan_LM": round(float(bp_stat), 3), "breusch_pagan_p": float(f"{bp_p:.3g}"),
            "jarque_bera": round(float(jb_stat), 3), "jarque_bera_p": float(f"{jb_p:.3g}"),
            "resid_skew": round(float(skew), 3), "resid_kurtosis": round(float(kurt), 3),
            "durbin_watson": round(float(durbin_watson(full.resid)), 3),
            "condition_number": round(float(full.condition_number), 1),
            "max_vif": float(vif["vif"].max()), "vars_vif_over_5": vif.query("vif > 5")["variable"].tolist()}
    pd.Series(diag).to_csv(OUT / "rq2_diagnostics.csv", header=["value"])
    model_cmp = pd.DataFrame({
        "model": ["Restricted (ASR only)", "Full (ASR + 11 attributes)"],
        "k": [1, k], "R2": [r2r, r2f], "adj_R2": [restricted.rsquared_adj, full.rsquared_adj],
        "AIC": [restricted.aic, full.aic], "BIC": [restricted.bic, full.bic],
        "RMSE_log": [np.sqrt(restricted.mse_resid), np.sqrt(full.mse_resid)]}).round(4)
    model_cmp.to_csv(OUT / "rq2_model_comparison.csv", index=False)
    (OUT / "rq2_full_model_summary.txt").write_text(f"{label}\n\n{full_hc3.summary()}")

    # 5. figures
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].scatter(full.fittedvalues, full.resid, s=8, alpha=0.4, color=SERIES[0])
    axes[0].axhline(0, color=INK_2, lw=1.2)
    axes[0].set_xlabel("Fitted ln value per m²"); axes[0].set_ylabel("Residual")
    axes[0].set_title("Residuals vs. fitted (full model)")
    sm.qqplot(full.resid, line="45", fit=True, ax=axes[1], markersize=3, alpha=0.5,
              markerfacecolor=SERIES[0], markeredgecolor=SERIES[0])
    axes[1].get_lines()[1].set_color(INK_2)
    axes[1].set_title("Normal Q–Q plot of residuals")
    fig.tight_layout(); footer(fig, label); fig.savefig(OUT / "fig_rq2_diagnostics.png"); plt.close(fig)

    c = coef[coef["variable"] != "const"].sort_values("std_beta")
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    cols = [SERIES[0] if s else "#b9b8b3" for s in c["significant_hc3"]]
    ax.barh(c["term"], c["std_beta"], color=cols)
    ax.axvline(0, color=INK_2, lw=1)
    ax.set_xlabel("Standardized coefficient (β)")
    ax.set_title("RQ2 — Drivers of ln value per m² (blue = p < .05, HC3)")
    footer(fig, label); fig.savefig(OUT / "fig_rq2_standardized_coefficients.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4.2))
    ax.bar(["Restricted\n(ASR only)", "Full\n(+11 attributes)"], [r2r, r2f], color=[INK_2, SERIES[0]], width=0.5)
    for i, v in enumerate([r2r, r2f]):
        ax.text(i, v + 0.01, f"{v:.3f}", ha="center")
    ax.set_ylim(0, 1.05); ax.set_ylabel("R²")
    ax.set_title(f"RQ2 — ΔR² = {r2f - r2r:.3f}, F({u}, {n - k - 1}) = {F:.1f}")
    footer(fig, label); fig.savefig(OUT / "fig_rq2_r2_increase.png"); plt.close(fig)

    sig = coef[(coef["variable"].isin(ATTRS)) & coef["significant_hc3"]]
    summary = {
        "n": n, "k_full": k, "u_tested": u,
        "R2_restricted": round(r2r, 4), "R2_full": round(r2f, 4), "delta_R2": round(r2f - r2r, 4),
        "adj_R2_full": round(full.rsquared_adj, 4), "cohens_f2_increment": round(f2, 4),
        "partial_F": round(F, 3), "df": [u, n - k - 1], "p_partial_F": float(f"{p_F:.3g}"),
        "robust_wald_F_HC3": round(float(np.squeeze(wald.fvalue)), 3), "robust_wald_p": float(f"{float(wald.pvalue):.3g}"),
        "decision_alpha_0.05": "Reject H0: attributes add explanatory power" if p_F < ALPHA else "Fail to reject H0",
        "asr_elasticity": round(float(b_asr), 4), "asr_elasticity_ci95": [round(float(ci.loc['ln_asr_rate_m2', 0]), 4),
                                                                   round(float(ci.loc['ln_asr_rate_m2', 1]), 4)],
        "test_asr_elasticity_eq_1_p": float(f"{p_asr1:.3g}"),
        "significant_attributes_hc3": sig["term"].tolist(),
        "not_significant_hc3": coef[(coef["variable"].isin(ATTRS)) & ~coef["significant_hc3"]]["term"].tolist(),
        "significant_under_cluster_se": coef[(coef["variable"].isin(ATTRS)) & coef["significant_cluster"]]["term"].tolist(),
        "top3_by_abs_std_beta": c.reindex(c["std_beta"].abs().sort_values(ascending=False).index)["term"].head(3).tolist(),
        "diagnostics": diag,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary, sorted(OUT.iterdir())
