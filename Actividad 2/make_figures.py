"""Genera las figuras del informe (PNG a 300 dpi) a partir de los CSV de data/.

Uso (desde la carpeta Actividad 2/):
    python make_figures.py [--data data] [--out figures]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from hmm_churn.metrics import align_permutation, summarize  # noqa: E402
from hmm_churn.model import SCENARIOS, STATES, SYMBOLS  # noqa: E402
from hmm_churn.simulate import simulate  # noqa: E402
from run_experiments import SCENARIO_ORDER, _fit  # noqa: E402

DPI = 300
WIDTH = 6.5  # pulgadas: ancho útil de una página carta con márgenes
STATE_COLORS = ["#009E73", "#E69F00", "#D55E00"]  # paleta Okabe-Ito
SYMBOL_COLORS = ["#E8E8E8", "#0072B2", "#CC79A7", "#000000"]
STATE_NAMES = ["Fidelizado (F)", "En riesgo (R)", "Abandono inminente (A)"]
SYMBOL_NAMES = ["Sin novedad (N)", "Reclamo técnico (T)", "Pago tardío (P)", "Contacto retención/baja (C)"]
SCENARIO_LABELS = {"base": "Base", "mala_red": "Mala red", "retencion": "Retención"}

plt.rcParams.update({
    "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
    "legend.fontsize": 7, "savefig.dpi": DPI, "figure.dpi": 100,
    "axes.spines.top": False, "axes.spines.right": False,
})


def _save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def fig_trajectories(out: Path) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(WIDTH, 6.4), constrained_layout=True)
    cmap_s = ListedColormap(STATE_COLORS)
    cmap_o = ListedColormap(SYMBOL_COLORS)
    for row, name in enumerate(SCENARIO_ORDER):
        states, obs = simulate(SCENARIOS[name], n_clients=5, n_weeks=52, seed=7)
        axes[row, 0].imshow(states, aspect="auto", cmap=cmap_s, vmin=0, vmax=2,
                            interpolation="nearest")
        axes[row, 1].imshow(obs, aspect="auto", cmap=cmap_o, vmin=0, vmax=3,
                            interpolation="nearest")
        axes[row, 0].set_title(f"Estados ocultos, escenario {SCENARIO_LABELS[name]}")
        axes[row, 1].set_title(f"Observaciones, escenario {SCENARIO_LABELS[name]}")
        for ax in axes[row]:
            ax.set_ylabel("Cliente")
            ax.set_yticks(range(5), labels=[str(i + 1) for i in range(5)])
            ax.spines[:].set_visible(False)
        if row == 2:
            for ax in axes[row]:
                ax.set_xlabel("Semana")
    handles = [Patch(color=c, label=n) for c, n in zip(STATE_COLORS, STATE_NAMES)]
    handles += [Patch(facecolor=c, edgecolor="#999999", label=n)
                for c, n in zip(SYMBOL_COLORS, SYMBOL_NAMES)]
    fig.legend(handles=handles, loc="outside lower center", ncol=4, frameon=False)
    _save(fig, out / "fig1_trayectorias.png")


def fig_accuracy(data: Path, out: Path) -> None:
    raw = pd.read_csv(data / "resultados_crudos.csv")
    summ = pd.read_csv(data / "resumen_escenarios.csv")
    fig, ax = plt.subplots(figsize=(WIDTH, 3.4), constrained_layout=True)
    series = [("viterbi_acc", "Parámetros verdaderos", "#0072B2", -0.18),
              ("viterbi_acc_bw", "Parámetros estimados (Baum-Welch)", "#E69F00", 0.18)]
    rng = np.random.default_rng(0)  # solo para el desplazamiento visual de los puntos
    for metric, label, color, shift in series:
        xs, means, lows, highs = [], [], [], []
        for i, name in enumerate(SCENARIO_ORDER):
            row = summ[(summ.scenario == name) & (summ.metric == metric)].iloc[0]
            xs.append(i + shift)
            means.append(row["mean"])
            lows.append(row["mean"] - row["ci_low"])
            highs.append(row["ci_high"] - row["mean"])
            vals = raw.loc[raw.scenario == name, metric]
            ax.scatter(i + shift + rng.uniform(-0.07, 0.07, len(vals)), vals,
                       s=7, color=color, alpha=0.35, linewidths=0)
        ax.errorbar(xs, means, yerr=[lows, highs], fmt="o", color=color, capsize=4,
                    markersize=5, label=label, zorder=3)
    ax.set_xticks(range(3), labels=[SCENARIO_LABELS[n] for n in SCENARIO_ORDER])
    ax.set_xlabel("Escenario")
    ax.set_ylabel("Precisión de Viterbi\n(fracción de estados correctos)")
    ax.set_title("Recuperación del estado oculto por escenario (media e IC 95 %, 30 semillas)")
    ax.legend(loc="lower right", frameon=False)
    ax.grid(axis="y", alpha=0.25)
    _save(fig, out / "fig2_precision_escenarios.png")


def _mean_ci(df: pd.DataFrame, level_col: str, value_col: str):
    levels, means, lows, highs = [], [], [], []
    for level, grp in df.groupby(level_col, sort=True):
        vals = grp[value_col].dropna()
        if vals.empty:
            continue
        s = summarize(vals)
        levels.append(level)
        means.append(s["mean"])
        lows.append(s["mean"] - s["ci_low"])
        highs.append(s["ci_high"] - s["mean"])
    return levels, np.array(means), np.array([lows, highs])


def fig_sensitivity(data: Path, out: Path) -> None:
    sens = pd.read_csv(data / "sensibilidad.csv")
    fig, axes = plt.subplots(2, 2, figsize=(WIDTH, 5.2), constrained_layout=True)

    t = sens[sens.factor == "T_semanas"].copy()
    t["level"] = pd.to_numeric(t["level"])
    lv, m, e = _mean_ci(t, "level", "viterbi_acc")
    axes[0, 0].errorbar(lv, m, yerr=e, fmt="o-", color="#0072B2", capsize=3)
    axes[0, 0].set_xlabel("Longitud de la secuencia (semanas)")
    axes[0, 0].set_ylabel("Precisión de Viterbi")
    axes[0, 0].set_title("(a) Precisión según la longitud")

    for col, color, label in (("err_A", "#D55E00", "Error en A"), ("err_B", "#009E73", "Error en B")):
        lv, m, e = _mean_ci(t, "level", col)
        axes[0, 1].errorbar(lv, m, yerr=e, fmt="o-", color=color, capsize=3, label=label)
    axes[0, 1].set_xlabel("Longitud de la secuencia (semanas)")
    axes[0, 1].set_ylabel("Error de Frobenius tras Baum-Welch")
    axes[0, 1].set_title("(b) Recuperación de parámetros")
    axes[0, 1].legend(frameon=False)

    d = sens[sens.factor == "A_diagonal"].copy()
    d["level"] = pd.to_numeric(d["level"])
    lv, m, e = _mean_ci(d, "level", "viterbi_acc")
    axes[1, 0].errorbar(lv, m, yerr=e, fmt="o-", color="#CC79A7", capsize=3)
    axes[1, 0].axvline(0, color="#999999", lw=0.8, ls="--")
    axes[1, 0].set_xlabel("Cambio en la diagonal de A (decodificación mal especificada)")
    axes[1, 0].set_ylabel("Precisión de Viterbi")
    axes[1, 0].set_title("(c) Sensibilidad a la matriz A")

    p = sens[sens.factor == "pi"]
    lv, m, e = _mean_ci(p, "level", "viterbi_acc")
    labels = {"base": "π del modelo", "uniforme": "π uniforme"}
    axes[1, 1].bar([labels[x] for x in lv], m, yerr=e, color=["#0072B2", "#E69F00"], capsize=4)
    axes[1, 1].set_ylim(max(0, float(np.min(m)) - 0.03), min(1, float(np.max(m)) + 0.03))
    axes[1, 1].set_ylabel("Precisión de Viterbi")
    axes[1, 1].set_title("(d) Sensibilidad a π")

    for ax in axes.ravel():
        ax.grid(axis="y", alpha=0.25)
    _save(fig, out / "fig3_sensibilidad.png")


def _heatmap(ax, M: np.ndarray, title: str) -> None:
    im = ax.imshow(M, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(3), labels=STATES)
    ax.set_yticks(range(3), labels=STATES)
    ax.set_xlabel("Estado siguiente")
    ax.set_ylabel("Estado actual")
    ax.set_title(title)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center",
                    color="white" if M[i, j] > 0.55 else "black", fontsize=8)
    ax.spines[:].set_visible(False)
    return im


def fig_matrices(out: Path) -> None:
    base = SCENARIOS["base"]
    _, obs = simulate(base, n_clients=200, n_weeks=52, seed=1)
    est, _ = _fit(base, obs, 1)
    est = align_permutation(base, est)
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 3.0), constrained_layout=True)
    _heatmap(axes[0], base.A, "Matriz A verdadera (escenario base)")
    im = _heatmap(axes[1], est.A, "Matriz A estimada con Baum-Welch")
    fig.colorbar(im, ax=axes, shrink=0.8, label="Probabilidad de transición")
    _save(fig, out / "fig4_matrices_A.png")


def fig_flow(out: Path) -> None:
    from matplotlib.patches import FancyBboxPatch

    steps = [
        ("1. Modelo", "λ = (π, A, B)\npor escenario"),
        ("2. Simular", "200 clientes ×\n52 semanas, semilla fija"),
        ("3. Decodificar", "Viterbi con los\nparámetros verdaderos"),
        ("4. Ajustar", "Baum-Welch\ncon 3 reinicios"),
        ("5. Evaluar", "precisión, recall,\nerror de A, B y π"),
        ("6. Estadística", "media, DE, IC 95 %,\nWelch, d de Cohen"),
        ("7. Sensibilidad", "longitud T, matriz A,\ndistribución π"),
        ("8. Resultados", "CSV, tablas\ny figuras"),
    ]
    fig, ax = plt.subplots(figsize=(WIDTH, 2.7))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 40)
    ax.axis("off")
    w, h, gap = 21.5, 15, 3.6
    xs = [1.4 + i * (w + gap) for i in range(4)]
    positions = [(xs[i], 23) for i in range(4)] + [(xs[3 - i], 2) for i in range(4)]
    for (title, body), (x, y) in zip(steps, positions):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.5",
                                    fc="#F2F6FA", ec="#0072B2", lw=1))
        ax.text(x + w / 2, y + h - 3.2, title, ha="center", va="center", fontsize=7.5,
                fontweight="bold")
        ax.text(x + w / 2, y + h / 2 - 2, body, ha="center", va="center", fontsize=6)
    for k in range(len(steps) - 1):
        (x0, y0), (x1, y1) = positions[k], positions[k + 1]
        if k < 3:
            start, end = (x0 + w + 0.5, y0 + h / 2), (x1 - 0.5, y1 + h / 2)
        elif k == 3:
            start, end = (x0 + w / 2, y0 - 0.5), (x1 + w / 2, y1 + h + 0.5)
        else:
            start, end = (x0 - 0.5, y0 + h / 2), (x1 + w + 0.5, y1 + h / 2)
        ax.annotate("", xy=end, xytext=start,
                    arrowprops=dict(arrowstyle="-|>", color="#444444", lw=1))
    _save(fig, out / "fig5_flujo_metodologico.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--out", type=Path, default=ROOT / "figures")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    fig_trajectories(args.out)
    fig_accuracy(args.data, args.out)
    fig_sensitivity(args.data, args.out)
    fig_matrices(args.out)
    fig_flow(args.out)


if __name__ == "__main__":
    main()
