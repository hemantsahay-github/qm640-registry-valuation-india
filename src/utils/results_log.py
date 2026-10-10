"""
results_log.py — Append a dated, RQ-labelled entry to docs/RESULTS_LOG.md after
every stage, so each run is traceable for the synopsis, interim and final
reports. Also stamps whether the run used SYNTHETIC validation data.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.config import RESULTS_LOG


def data_label(is_synthetic: bool) -> str:
    return ("PIPELINE VALIDATION — SYNTHETIC DATA (not study findings)"
            if is_synthetic else "STUDY DATA — Maharashtra Index-II (de-identified)")


def log_stage(stage: str, is_synthetic: bool, summary: dict, files: list[Path],
              interpretation: str = "") -> None:
    RESULTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not RESULTS_LOG.exists():
        RESULTS_LOG.write_text("# Results Log — QM 640 Capstone\n\n"
                               "Each entry is written automatically by `src/pipeline.py`.\n\n")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"## {stage} — {ts}", "", f"**Data:** {data_label(is_synthetic)}", "",
             "**Key results**", "", "```json", json.dumps(summary, indent=2, default=str), "```", ""]
    if interpretation:
        lines += ["**Interpretation**", "", interpretation, ""]
    lines += ["**Output files**", ""] + [f"- `{f.as_posix()}`" for f in files] + ["", "---", ""]
    with open(RESULTS_LOG, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
