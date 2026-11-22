"""Lee data/*.csv y genera las figuras PNG (300 dpi) en figures/."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, Patch

import banco

ROOT = Path(__file__).parent
DATA, FIGS = ROOT / "data", ROOT / "figures"
FIGS.mkdir(exist_ok=True)

AZUL, NARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
TINTA, TINTA2, GRIS = "#0b0b0b", "#52514e", "#d9d8d4"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GRIS, "axes.labelcolor": TINTA2,
    "xtick.color": TINTA2, "ytick.color": TINTA2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#eeeeec", "grid.linewidth": 0.8, "axes.axisbelow": True,
    "savefig.dpi": 300, "savefig.bbox": "tight", "figure.facecolor": "white",
})
ETIQ = dict(banco.DESCRIPCION)
ESC = list(banco.ESCENARIOS)


def guardar(fig, nombre):
    fig.savefig(FIGS / nombre)
    plt.close(fig)


crit = pd.read_csv(DATA / "resumen_espera_criterio.csv")

# Fig. 1: espera general por escenario
g = crit[crit.criterio == "General"].set_index("escenario").loc[ESC]
fig, ax = plt.subplots(figsize=(6.4, 2.8))
y = np.arange(len(ESC))[::-1]
ax.barh(y, g.media, height=0.55, color=AZUL, xerr=[g.media - g.ic_inf, g.ic_sup - g.media],
        error_kw=dict(ecolor=TINTA2, lw=1, capsize=3))
xmax = g.ic_sup.max() * 1.05
for yi, m in zip(y, g.media):
    ax.text(xmax + 0.1, yi, f"{m:.2f} min", va="center", fontsize=8, color=TINTA)
ax.set_xlim(0, xmax + 1.0)
ax.axvline(5, color=TINTA2, ls="--", lw=1)
ax.text(5.05, y[-1] - 0.45, "umbral 5 min", fontsize=7.5, color=TINTA2)
ax.set_yticks(y, [ETIQ[e] for e in ESC])
ax.set_xlabel("Tiempo promedio de espera en cola (min), IC 95 %, 10 réplicas")
ax.grid(axis="y", visible=False)
guardar(fig, "fig1_espera_escenarios.png")

# Fig. 2: espera por operación y escenario
fig, ax = plt.subplots(figsize=(6.4, 3.0))
x = np.arange(len(ESC))
for k, (op, col) in enumerate([("Retiro", AZUL), ("Pago", NARANJA)]):
    h = crit[crit.criterio == f"Operación: {op}"].set_index("escenario").loc[ESC]
    ax.bar(x + (k - 0.5) * 0.36, h.media, width=0.34, color=col, label=op,
           yerr=[h.media - h.ic_inf, h.ic_sup - h.media], error_kw=dict(ecolor=TINTA2, lw=1, capsize=2))
ax.axhline(5, color=TINTA2, ls="--", lw=1)
CORTO = {"E0_3mixtas": "3 mixtas\n(actual)", "E1_1R_2P": "1 retiros\n+ 2 pagos", "E2_2R_1P": "2 retiros\n+ 1 pagos",
         "E3_4mixtas": "4 mixtas\n(caja nueva)", "E4_2R_2P": "2 retiros + 2 pagos\n(caja nueva)"}
ax.set_xticks(x, [CORTO[e] for e in ESC], fontsize=7.5)
ax.set_ylabel("Espera promedio (min), IC 95 %")
ax.legend(frameon=False, title="Operación", title_fontsize=8)
ax.grid(axis="x", visible=False)
guardar(fig, "fig2_espera_operacion.png")

# Fig. 3: tiempo promedio de atención por caja (escenarios de 3 cajas)
rc = pd.read_csv(DATA / "resumen_caja.csv")
rc = rc[rc.metrica == "t_atencion"]
fig, axs = plt.subplots(1, 3, figsize=(6.6, 2.6), sharey=True)
for ax, esc in zip(axs, ["E0_3mixtas", "E1_1R_2P", "E2_2R_1P"]):
    h = rc[rc.escenario == esc]
    ops = banco.ESCENARIOS[esc]
    cols = [AQUA if len(o) == 2 else (AZUL if o == ("Retiro",) else NARANJA) for o in ops]
    ax.bar(h.caja, h.media, color=cols, width=0.6,
           yerr=[h.media - h.ic_inf, h.ic_sup - h.media], error_kw=dict(ecolor=TINTA2, lw=1, capsize=3))
    for c, m in zip(h.caja, h.media):
        ax.text(c, 0.15, f"{m:.2f}", ha="center", fontsize=7.5, color="white", fontweight="bold")
    ax.set_title(ETIQ[esc].replace(" (situación actual)", "\n(actual)").replace(" + ", " +\n"), fontsize=8)
    ax.set_xticks([1, 2, 3], ["Caja 1", "Caja 2", "Caja 3"])
    ax.grid(axis="x", visible=False)
axs[0].set_ylabel("Tiempo de atención (min)")
fig.legend(handles=[Patch(color=AQUA, label="Mixta"), Patch(color=AZUL, label="Solo retiros"),
                    Patch(color=NARANJA, label="Solo pagos")], loc="lower center", ncol=3, frameon=False,
           bbox_to_anchor=(0.5, -0.06), fontsize=8)
guardar(fig, "fig3_atencion_caja.png")

# Fig. 4: usuarios por tipo en cada réplica (mapa de calor)
ut = pd.read_csv(DATA / "usuarios_tipo_replica.csv", index_col=0)
m = ut.drop(columns="Total")
fig, ax = plt.subplots(figsize=(6.6, 3.4))
im = ax.imshow(m.values, cmap="Blues", aspect="auto", vmin=0)
for i in range(m.shape[0]):
    for j in range(m.shape[1]):
        v = m.values[i, j]
        mn = v == m.iloc[:, j].min()
        ax.text(j, i, str(v), ha="center", va="center", fontsize=7.5,
                color="white" if v > m.values.max() * 0.55 else TINTA, fontweight="bold" if mn else "normal",
                bbox=dict(boxstyle="round,pad=0.15", fc="none", ec=NARANJA, lw=1.2) if mn else None)
ax.set_xticks(range(m.shape[1]), [c.replace(" - ", "\n") for c in m.columns], fontsize=7)
ax.set_yticks(range(m.shape[0]), [f"Réplica {r}" for r in m.index], fontsize=7.5)
ax.grid(False)
for s in ax.spines.values():
    s.set_visible(False)
cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
cb.set_label("Usuarios por día", fontsize=8)
cb.outline.set_visible(False)
guardar(fig, "fig4_usuarios_tipo_replica.png")

# Fig. 5: evolución de la cola durante el día (réplica 1)
reg = pd.read_csv(DATA / "registros.csv")
t = np.linspace(0, 500, 1001)
fig, axs = plt.subplots(3, 1, figsize=(6.6, 4.6), sharex=True, sharey=True)
for ax, esc in zip(axs, ["E0_3mixtas", "E1_1R_2P", "E2_2R_1P"]):
    r = reg[(reg.escenario == esc) & (reg.replica == 1)]
    for op, col in [("Retiro", AZUL), ("Pago", NARANJA)]:
        q = r[r.operacion == op]
        cola = ((q.llegada.values[:, None] <= t) & (t < q.inicio.values[:, None])).sum(axis=0)
        ax.step(t, cola, where="post", color=col, lw=1.4, label=op)
    ax.set_title(ETIQ[esc], fontsize=8, loc="left")
    ax.axvline(480, color=TINTA2, ls=":", lw=1)
axs[0].legend(frameon=False, ncol=2, fontsize=8, loc="upper right")
axs[1].set_ylabel("Personas en cola")
axs[2].set_xlabel("Minuto de la jornada (línea punteada: cierre de puertas a los 480 min)")
guardar(fig, "fig5_cola_tiempo.png")

# Fig. 6: diagrama del modelo
fig, ax = plt.subplots(figsize=(7.2, 2.6))
ax.set_xlim(0, 12.4)
ax.set_ylim(0, 4)
ax.axis("off")


def caja_txt(x, y, w, h, txt, fc="#f3f3f1"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=fc, ec=TINTA2, lw=0.8))
    ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=6.6, color=TINTA)


def flecha(x1, y1, x2, y2):
    ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="->", color=TINTA2, lw=0.9))


caja_txt(0.1, 1.5, 1.9, 1.0, "Llegada\n(puerta abierta\n0 a 480 min)")
caja_txt(2.5, 1.5, 2.3, 1.0, "Sorteo operación\nRetiro 70 % / Pago 30 %\ny tipo (Tabla 2)")
caja_txt(5.3, 1.5, 2.3, 1.0, "Llegada ~ Exp(media)\nServicio ~ Exp(media)\n(Tabla 1)")
caja_txt(8.1, 1.5, 2.0, 1.0, "Elige la caja\nhabilitada con\nmenos personas")
for i, yy in enumerate([3.0, 1.75, 0.5]):
    caja_txt(10.7, yy, 1.6, 0.6, f"Caja {i + 1}\nM/M/1 (FIFO)", fc="#e6eef9")
    flecha(10.15, 2.0, 10.65, yy + 0.3)
flecha(2.05, 2.0, 2.45, 2.0)
flecha(4.85, 2.0, 5.25, 2.0)
flecha(7.65, 2.0, 8.05, 2.0)
guardar(fig, "fig6_modelo.png")
print("figuras en", FIGS)
