"""
sample_size_final.py — Final-report minimum sample size (Table 8, Appendix A).

Every input is printed so a reader can verify each step:
alpha, power, z values, ICC, cluster size, design effect, and the RQ-specific
effect sizes. Writes outputs/sample_size_final.csv.

Run : python scripts/sample_size_final.py
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
from scipy import stats

ALPHA, POWER = 0.05, 0.80
Z_A, Z_B = stats.norm.ppf(1 - ALPHA / 2), stats.norm.ppf(POWER)
ICC, M = 0.02, 20                         # intraclass correlation; mean sales per micro-market
DEFF = 1 + (M - 1) * ICC                  # Kish (1965) design effect


def rq1(p=0.50, e=0.03):
    n0 = Z_A ** 2 * p * (1 - p) / e ** 2
    n = math.ceil(n0 * DEFF)
    print(f"RQ1  inputs: alpha={ALPHA}, z={Z_A:.4f}, p={p}, e={e}, ICC={ICC}, m={M}, DEFF={DEFF:.2f}")
    print(f"     n0 = {Z_A:.4f}^2 x {p} x {1-p} / {e}^2 = {n0:.2f}; n = n0 x DEFF = {n0*DEFF:.2f} -> {n}")
    return n


def rq2(f2=0.02, u=11, clusters=67):
    df2 = clusters - 1
    f_crit = stats.f.ppf(1 - ALPHA, u, df2)
    for n in range(100, 5000, 10):
        lam = f2 * n / DEFF
        pw = 1 - stats.ncf.cdf(f_crit, u, df2, lam)
        if pw >= POWER:
            print(f"RQ2  inputs: alpha={ALPHA}, power={POWER}, f2={f2}, u={u}, clusters G={clusters}, DEFF={DEFF:.2f}")
            print(f"     N = {n}: N_eff = {n/DEFF:.1f}, lambda = {lam:.2f}, F_crit({u}, {df2}) = {f_crit:.3f}, power = {pw:.3f}")
            return n
    raise RuntimeError


def rq3(dz=0.75, floor_mm=40, per_mm=20):
    g = ((Z_A + Z_B) / dz) ** 2 + Z_A ** 2 / 2
    print(f"RQ3  inputs: alpha={ALPHA}, power={POWER}, dz={dz}, design floor {floor_mm} micro-markets x {per_mm} sales")
    print(f"     G = ({Z_A + Z_B:.4f} / {dz})^2 + {Z_A**2/2:.2f} = {g:.2f} -> {math.ceil(g)} micro-markets; "
          f"floor = {floor_mm} x {per_mm} = {floor_mm*per_mm}")
    return max(math.ceil(g) * per_mm, floor_mm * per_mm)


def rq4(P=0.12, OR=1.5, rho2=0.30, k=12, epv=10):
    b2 = math.log(OR) ** 2
    nh = (Z_A + Z_B) ** 2 / (P * (1 - P) * b2)
    n_adj = math.ceil(nh / (1 - rho2) * DEFF)
    n_epv = math.ceil(epv * k / P)
    print(f"RQ4  inputs: alpha={ALPHA}, power={POWER}, P={P}, OR={OR} per SD, rho2={rho2}, k={k}, EPV={epv}, DEFF={DEFF:.2f}")
    print(f"     Hsieh n = {(Z_A+Z_B)**2:.4f} / ({P} x {1-P:.2f} x {b2:.4f}) = {nh:.2f}; / (1 - {rho2}) x {DEFF:.2f} = {n_adj}")
    print(f"     EPV n = {epv} x {k} / {P} = {n_epv}; adopted = {max(n_adj, n_epv)}")
    return max(n_adj, n_epv)


def main():
    ns = {"RQ1": rq1(), "RQ2": rq2(), "RQ3": rq3(), "RQ4": rq4()}
    final = max(ns.values())
    target = math.ceil(final / 0.60 / 100) * 100
    print(f"FINAL N = max({', '.join(str(v) for v in ns.values())}) = {final}; "
          f"collection target allowing 40% exclusions = {target} raw records")
    Path("outputs").mkdir(exist_ok=True)
    pd.DataFrame({"rq": list(ns) + ["FINAL"], "min_n": list(ns.values()) + [final]}).to_csv(
        "outputs/sample_size_final.csv", index=False)


if __name__ == "__main__":
    main()
