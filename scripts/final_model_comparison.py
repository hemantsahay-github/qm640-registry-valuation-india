"""
final_model_comparison.py — Final-report model comparison (Tables 12-13, Figures 5-8, 11).

Reuses the pipeline's design matrix, split, and metric functions so every number
matches the RQ3/RQ4 stages. Adds the random forest and MLP benchmarks, training-
versus-test metrics, labelled confusion matrices (Anchored / Not anchored) for
training and test data, and permutation feature importance on held-out data.

Run : python scripts/final_model_comparison.py
Out : outputs/final/*.csv, outputs/final/summary.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import confusion_matrix, roc_auc_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier, XGBRegressor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ANALYSIS_FILE, OUTPUT_DIR, RANDOM_SEED, TEST_GROUP_SHARE  # noqa: E402
from src.models.rq2_hedonic import LABELS, design  # noqa: E402
from src.models.rq3_gbm_vs_ols import features, metrics  # noqa: E402
from src.models.rq4_anchoring import classification_metrics, youden_threshold  # noqa: E402

OUT = OUTPUT_DIR / "final"


def mlp() -> object:
    return make_pipeline(StandardScaler(), MLPRegressor(hidden_layer_sizes=(64, 32, 16), alpha=3.0, early_stopping=True,
                                                         max_iter=2000, random_state=RANDOM_SEED))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(ANALYSIS_FILE)
    X_ols, X_ml = features(df)
    y, groups = df["ln_value_m2"].to_numpy(), df["micro_market"].to_numpy()
    tr, te = next(GroupShuffleSplit(1, test_size=TEST_GROUP_SHARE, random_state=RANDOM_SEED).split(X_ols, y, groups))
    params = json.loads((OUTPUT_DIR / "rq3" / "best_params.json").read_text())

    makers = {
        "OLS": lambda: LinearRegression(),
        "XGBoost": lambda: XGBRegressor(objective="reg:squarederror", random_state=RANDOM_SEED,
                                        tree_method="hist", n_jobs=4, **params),
        "Random forest": lambda: RandomForestRegressor(n_estimators=500, min_samples_leaf=5,
                                                       random_state=RANDOM_SEED, n_jobs=4),
        "MLP": mlp,
    }
    Xs = {"OLS": X_ols, "XGBoost": X_ml, "Random forest": X_ml, "MLP": X_ols}
    rows, preds, fitted = [], {}, {}
    for name, make in makers.items():
        X = Xs[name]
        m = make().fit(X.iloc[tr], y[tr])
        p_tr, p_te = m.predict(X.iloc[tr]), m.predict(X.iloc[te])
        preds[name], fitted[name] = p_te, m
        cv = []
        for a, b in GroupKFold(n_splits=5).split(X, y, groups):
            mm = make().fit(X.iloc[a], y[a])
            cv.append(np.mean(np.abs(y[b] - mm.predict(X.iloc[b]))))
        mtr, mte = metrics(y[tr], p_tr), metrics(y[te], p_te)
        rows.append({"model": name, "train_MAE": mtr["MAE_log"], "test_MAE": mte["MAE_log"],
                     "test_RMSE": mte["RMSE_log"], "test_R2": mte["R2_log"], "test_MAPE": mte["MAPE_pct"],
                     "test_MAE_inr_m2": mte["MAE_inr_m2"], "cv_MAE": float(np.mean(cv)),
                     "cv_MAE_sd": float(np.std(cv, ddof=1))})
    comp = pd.DataFrame(rows).round(4)
    comp.to_csv(OUT / "value_model_comparison.csv", index=False)

    e_ols = np.abs(y[te] - preds["OLS"])
    paired = []
    for name in ["XGBoost", "Random forest", "MLP"]:
        d = e_ols - np.abs(y[te] - preds[name])
        t, p2 = stats.ttest_rel(e_ols, np.abs(y[te] - preds[name]))
        paired.append({"model": name, "mean_d": d.mean(), "t": t, "df": len(te) - 1,
                       "p_one_sided": p2 / 2 if t > 0 else 1 - p2 / 2})
    pd.DataFrame(paired).round(5).to_csv(OUT / "paired_tests_vs_ols.csv", index=False)
    pd.DataFrame({"actual": y[te], **{k: v for k, v in preds.items()}}).to_csv(OUT / "test_predictions.csv", index=False)

    # permutation importance on held-out micro-markets (MAE increase when a feature is shuffled)
    imp = []
    for name in ["OLS", "XGBoost"]:
        r = permutation_importance(fitted[name], Xs[name].iloc[te], y[te], scoring="neg_mean_absolute_error",
                                   n_repeats=30, random_state=RANDOM_SEED)
        for f, mu, sd in zip(Xs[name].columns, r.importances_mean, r.importances_std):
            imp.append({"model": name, "feature": f, "label": LABELS.get(f, {"lat": "Latitude", "lon": "Longitude"}.get(f, f)),
                        "mae_increase": mu, "sd": sd})
    pd.DataFrame(imp).round(5).to_csv(OUT / "permutation_importance.csv", index=False)

    # ---- anchoring classifiers: training and test metrics + labelled confusion matrices
    Xa, ya = design(df), df["anchored"].to_numpy()
    lg = sm.Logit(ya[tr], sm.add_constant(Xa.iloc[tr])).fit(disp=0, maxiter=200)
    p_lg_tr = lg.predict(sm.add_constant(Xa.iloc[tr])).to_numpy()
    p_lg_te = lg.predict(sm.add_constant(Xa.iloc[te], has_constant="add")).to_numpy()
    thr = youden_threshold(ya[tr], p_lg_tr)
    cls = {"train": classification_metrics(ya[tr], p_lg_tr, thr), "test": classification_metrics(ya[te], p_lg_te, thr)}
    for part, yy, pp in [("train", ya[tr], p_lg_tr), ("test", ya[te], p_lg_te)]:
        cm = confusion_matrix(yy, (pp >= thr).astype(int), labels=[1, 0])
        pd.DataFrame(cm, index=["Actual: Anchored", "Actual: Not anchored"],
                     columns=["Predicted: Anchored", "Predicted: Not anchored"]).to_csv(OUT / f"confusion_logit_{part}.csv")
        cls[part]["accuracy"] = float((cm[0, 0] + cm[1, 1]) / cm.sum())
        cls[part]["n"], cls[part]["prevalence"] = int(len(yy)), float(yy.mean())
    pd.DataFrame(cls).to_csv(OUT / "classifier_train_test.csv")
    pd.DataFrame({"y": ya[te], "p_logit": p_lg_te}).to_csv(OUT / "classifier_test_scores.csv", index=False)

    summary = {"n_train": int(len(tr)), "n_test": int(len(te)), "logit_threshold": round(float(thr), 4),
               "value_models": comp.to_dict("records"), "paired": pd.DataFrame(paired).round(5).to_dict("records"),
               "logit_train": cls["train"], "logit_test": cls["test"],
               "logit_train_auc": float(roc_auc_score(ya[tr], p_lg_tr))}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print("=== FINAL MODEL COMPARISON ===")
    print(comp.to_string(index=False))
    print("\nPaired tests vs OLS (H1: model error < OLS error)")
    print(pd.DataFrame(paired).round(4).to_string(index=False))
    print(f"\nLogit threshold (Youden J, training) = {thr:.4f}")
    print(pd.DataFrame(cls).round(4).to_string())
    for part in ["train", "test"]:
        print(f"\nConfusion matrix — {part}")
        print(pd.read_csv(OUT / f"confusion_logit_{part}.csv", index_col=0).to_string())


if __name__ == "__main__":
    main()
