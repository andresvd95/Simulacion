"""Reproduce todos los experimentos de la actividad.

Uso (desde la carpeta Actividad 2/):
    python run_experiments.py            # corrida completa (30 semillas)
    python run_experiments.py --quick    # corrida corta para pruebas
"""
from __future__ import annotations

import argparse
import itertools
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from hmm_churn.algorithms import baum_welch_restarts, forward, viterbi  # noqa: E402
from hmm_churn.metrics import (  # noqa: E402
    best_permutation_accuracy,
    compare,
    param_error,
    per_state_recall,
    summarize,
    viterbi_accuracy,
)
from hmm_churn.model import HMM, SCENARIOS  # noqa: E402
from hmm_churn.simulate import simulate  # noqa: E402

SCENARIO_ORDER = ["base", "mala_red", "retencion"]
METRICS = [
    "viterbi_acc", "viterbi_acc_bw", "recall_F", "recall_R", "recall_A",
    "loglik_per_obs", "loglik_bw_gain", "bw_iters", "bw_converged", "err_A", "err_B", "err_pi",
]
BW_MAX_ITER = 200
BW_TOL = 1e-5  # relativa a la log-verosimilitud total
BW_N_INIT = 3  # arranques aleatorios por ajuste; se conserva el de mayor verosimilitud
INIT_MIX = 0.4  # peso del componente aleatorio en la inicialización de Baum-Welch
CSV_KW = dict(index=False, float_format="%.10g", lineterminator="\n")


def _decode_all(hmm: HMM, obs: np.ndarray) -> np.ndarray:
    return np.stack([viterbi(hmm, seq)[0] for seq in obs])


def _perturbed_init(hmm: HMM, rng: np.random.Generator) -> HMM:
    """Inicialización de Baum-Welch: mezcla de la verdad con filas Dirichlet(1)."""
    def mix_rows(M: np.ndarray) -> np.ndarray:
        D = rng.dirichlet(np.ones(M.shape[1]), size=M.shape[0])
        return (1 - INIT_MIX) * M + INIT_MIX * D

    pi = (1 - INIT_MIX) * hmm.pi + INIT_MIX * rng.dirichlet(np.ones(hmm.n_states))
    return HMM(pi=pi, A=mix_rows(hmm.A), B=mix_rows(hmm.B))


def _shift_diagonal(A: np.ndarray, delta: float) -> np.ndarray:
    """Suma `delta` a la diagonal y reescala el resto de cada fila para sumar 1."""
    out = A.copy()
    for i in range(A.shape[0]):
        d = float(np.clip(A[i, i] + delta, 0.01, 0.99))
        out[i] = A[i] * (1 - d) / (1 - A[i, i])
        out[i, i] = d
    return out


def _fit(hmm: HMM, obs: np.ndarray, seed: int):
    inits = [
        _perturbed_init(hmm, np.random.default_rng(seed + 500_000 + 7919 * k))
        for k in range(BW_N_INIT)
    ]
    est, _, iters = baum_welch_restarts(
        list(obs), inits, max_iter=BW_MAX_ITER, tol=BW_TOL
    )
    return est, iters


def _evaluate(hmm: HMM, seed: int, n_clients: int, n_weeks: int) -> dict:
    states, obs = simulate(hmm, n_clients, n_weeks, seed)
    paths = _decode_all(hmm, obs)
    recall = per_state_recall(states, paths)
    loglik = sum(forward(hmm, seq)[1] for seq in obs) / obs.size
    est, iters = _fit(hmm, obs, seed)
    err = param_error(hmm, est)
    acc_bw = best_permutation_accuracy(states, _decode_all(est, obs))
    loglik_est = sum(forward(est, seq)[1] for seq in obs) / obs.size
    return {
        "viterbi_acc": viterbi_accuracy(states, paths),
        "viterbi_acc_bw": acc_bw,
        "recall_F": recall[0], "recall_R": recall[1], "recall_A": recall[2],
        "loglik_per_obs": loglik, "bw_iters": iters,
        "bw_converged": int(iters < BW_MAX_ITER),
        "loglik_bw_gain": loglik_est - loglik,
        "err_A": err["A"], "err_B": err["B"], "err_pi": err["pi"],
    }


def _sensitivity(n_seeds: int, n_clients: int, n_weeks: int, lengths: list[int]) -> pd.DataFrame:
    base = SCENARIOS["base"]
    rows = []
    for seed in range(1, n_seeds + 1):
        for T in lengths:  # longitud de la secuencia: recuperación de parámetros
            states, obs = simulate(base, n_clients, T, seed)
            est, iters = _fit(base, obs, seed)
            err = param_error(base, est)
            acc = best_permutation_accuracy(states, _decode_all(est, obs))
            rows.append(dict(factor="T_semanas", level=T, seed=seed, viterbi_acc=acc,
                             err_A=err["A"], err_B=err["B"], bw_iters=iters))
        states, obs = simulate(base, n_clients, n_weeks, seed)
        for delta in (-0.10, -0.05, 0.05, 0.10):  # A mal especificada al decodificar
            wrong = HMM(pi=base.pi, A=_shift_diagonal(base.A, delta), B=base.B)
            acc = viterbi_accuracy(states, _decode_all(wrong, obs))
            rows.append(dict(factor="A_diagonal", level=delta, seed=seed, viterbi_acc=acc,
                             err_A=float(np.linalg.norm(wrong.A - base.A)),
                             err_B=np.nan, bw_iters=np.nan))
        for label, pi in (("base", base.pi), ("uniforme", np.full(3, 1 / 3))):
            wrong = HMM(pi=pi, A=base.A, B=base.B)
            acc = viterbi_accuracy(states, _decode_all(wrong, obs))
            rows.append(dict(factor="pi", level=label, seed=seed, viterbi_acc=acc,
                             err_A=np.nan, err_B=np.nan, bw_iters=np.nan))
    return pd.DataFrame(rows)


def _write_environment(out_dir: Path) -> None:
    import matplotlib
    import scipy
    lines = [
        f"python {platform.python_version()}",
        f"numpy {np.__version__}", f"pandas {pd.__version__}",
        f"scipy {scipy.__version__}", f"matplotlib {matplotlib.__version__}",
    ]
    try:
        import hmmlearn
        lines.append(f"hmmlearn {hmmlearn.__version__}")
    except ImportError:
        lines.append("hmmlearn no instalado")
    lines.append(f"plataforma {platform.platform()}")
    (out_dir / "entorno.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(n_seeds: int = 30, n_clients: int = 200, n_weeks: int = 52,
        out_dir: Path | None = None, lengths: list[int] | None = None) -> None:
    out_dir = Path(out_dir) if out_dir else ROOT / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    lengths = lengths or [13, 26, 52, 104]

    rows = []
    for idx, name in enumerate(SCENARIO_ORDER):
        for seed in range(1, n_seeds + 1):
            # semillas distintas por escenario: muestras independientes para la prueba de Welch
            result = _evaluate(SCENARIOS[name], seed + 1000 * idx, n_clients, n_weeks)
            rows.append({"scenario": name, "seed": seed, **result})
    raw = pd.DataFrame(rows)
    raw.to_csv(out_dir / "resultados_crudos.csv", **CSV_KW)

    summary = []
    for name in SCENARIO_ORDER:
        for metric in METRICS:
            values = raw.loc[raw.scenario == name, metric].dropna()
            summary.append({"scenario": name, "metric": metric, "n": len(values),
                            **summarize(values)})
    pd.DataFrame(summary).to_csv(out_dir / "resumen_escenarios.csv", **CSV_KW)

    comparisons = []
    for a, b in itertools.combinations(SCENARIO_ORDER, 2):
        for metric in METRICS:
            xa = raw.loc[raw.scenario == a, metric].dropna()
            xb = raw.loc[raw.scenario == b, metric].dropna()
            comparisons.append({"scenario_a": a, "scenario_b": b, "metric": metric,
                                **compare(xa, xb)})
    pd.DataFrame(comparisons).to_csv(out_dir / "comparacion_escenarios.csv", **CSV_KW)

    _sensitivity(n_seeds, n_clients, n_weeks, lengths).to_csv(
        out_dir / "sensibilidad.csv", **CSV_KW)
    _write_environment(out_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="corrida corta de verificación")
    parser.add_argument("--out", type=Path, default=None, help="carpeta de salida")
    args = parser.parse_args()
    if args.quick:
        run(n_seeds=3, n_clients=20, n_weeks=26, out_dir=args.out, lengths=[13, 26])
    else:
        run(out_dir=args.out)


if __name__ == "__main__":
    main()
