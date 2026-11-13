import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV_FILES = [
    "resultados_crudos.csv",
    "resumen_escenarios.csv",
    "comparacion_escenarios.csv",
    "sensibilidad.csv",
]


def _run_quick(out_dir: Path) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "run_experiments.py"), "--quick", "--out", str(out_dir)],
        check=True,
        cwd=ROOT,
    )


def test_quick_run_is_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _run_quick(a)
    _run_quick(b)  # proceso nuevo: no depende de estado en memoria
    for name in CSV_FILES:
        assert (a / name).read_bytes() == (b / name).read_bytes(), name


def test_raw_csv_has_expected_columns_and_rows(tmp_path):
    _run_quick(tmp_path)
    raw = pd.read_csv(tmp_path / "resultados_crudos.csv")
    expected = {
        "scenario", "seed", "viterbi_acc", "viterbi_acc_bw",
        "recall_F", "recall_R", "recall_A", "loglik_per_obs",
        "bw_iters", "bw_converged", "loglik_bw_gain", "err_A", "err_B", "err_pi",
    }
    assert expected <= set(raw.columns)
    assert len(raw) == 3 * 3  # 3 escenarios x 3 semillas en modo rápido
    assert set(raw["scenario"]) == {"base", "mala_red", "retencion"}
    assert raw[["viterbi_acc", "err_A"]].notna().all().all()


def test_summary_has_confidence_intervals(tmp_path):
    _run_quick(tmp_path)
    summary = pd.read_csv(tmp_path / "resumen_escenarios.csv")
    for col in ("mean", "std", "min", "max", "ci_low", "ci_high"):
        assert col in summary.columns
    row = summary[(summary.scenario == "base") & (summary.metric == "viterbi_acc")].iloc[0]
    assert row.ci_low <= row["mean"] <= row.ci_high
