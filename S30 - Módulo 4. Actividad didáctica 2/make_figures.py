"""Lee data/*.csv y genera las figuras PNG (300 dpi) en figures/ con Matplotlib."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

import parqueadero as pq

ROOT = Path(__file__).parent
DATA, FIGS = ROOT / "data", ROOT / "figures"
FIGS.mkdir(exist_ok=True)

AZUL, NARANJA, AQUA, MORADO = "#2a78d6", "#eb6834", "#1baf7a", "#8a5cd1"
TINTA, TINTA2, GRIS = "#0b0b0b", "#52514e", "#d9d8d4"
COL_TIPO = dict(zip(pq.TIPOS, [AQUA, AZUL, NARANJA, MORADO]))
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GRIS, "axes.labelcolor": TINTA2,
    "xtick.color": TINTA2, "ytick.color": TINTA2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#eeeeec", "grid.linewidth": 0.8, "axes.axisbelow": True,
    "savefig.dpi": 300, "savefig.bbox": "tight", "figure.facecolor": "white",
})
ESC = list(pq.ESCENARIOS)
par = pd.read_csv(DATA / "estado_estable.csv", index_col=0)["valor"]
T_WARM, NIVEL, N = par["t_transitorio_min"], par["nivel_estable_min"], int(par["replicas_usadas"])
N_ACUM, N_FORM = int(par["n_media_acumulada"]), int(par["n_formula_ic"])


def guardar(fig, nombre):
    fig.savefig(FIGS / nombre)
    plt.close(fig)


# Fig. 1: método de Welch (media sobre la variable "espera" por intervalo de 10 min)
w = pd.read_csv(DATA / "welch.csv")
fig, ax = plt.subplots(figsize=(6.6, 3.2))
ax.axvspan(0, T_WARM, color=GRIS, alpha=0.35, lw=0)
ax.plot(w.inicio_min, w.espera_media, color=AZUL, alpha=0.35, lw=1, label="Espera media por intervalo (100 réplicas)")
ax.plot(w.inicio_min, w.media_movil, color=AZUL, lw=2, label=f"Media móvil de Welch (ventana {2 * int(par['ventana_welch']) + 1})")
ax.axhline(NIVEL, color=TINTA2, ls="--", lw=1, label=f"Nivel estable {NIVEL:.1f} min")
ax.axhline(0.9 * NIVEL, color=TINTA2, ls=":", lw=1, label="90 % del nivel estable")
ax.axvline(T_WARM, color=NARANJA, lw=1.5)
ax.text(T_WARM / 2, NIVEL * 1.25, "Transitorio", ha="center", color=TINTA2, fontsize=8)
ax.text(T_WARM + 8, NIVEL * 1.13, f"fin del transitorio: {T_WARM:.0f} min", color=NARANJA, fontsize=8)
ax.set_xlabel("Minuto de la jornada (llegada del usuario)")
ax.set_ylabel("Espera en cola (min)")
ax.set_xlim(0, pq.HORIZONTE)
ax.set_ylim(0, None)
ax.legend(fontsize=7, frameon=False, loc="lower right")
guardar(fig, "fig1_welch.png")

# Fig. 2: media acumulada sobre las réplicas -> número de corridas
a = pd.read_csv(DATA / "media_acumulada.csv")
fig, ax = plt.subplots(figsize=(6.6, 3.2))
fin = a.media_acum_sin.iloc[-1]
ax.fill_between(a.replicas, 0.95 * fin, 1.05 * fin, color=AQUA, alpha=0.15, lw=0, label="±5 % del valor final")
ax.scatter(a.replicas, a.espera_replica_sin, s=6, color=GRIS, label="Espera media de cada réplica")
ax.plot(a.replicas, a.media_acum_sin, color=AQUA, lw=2, label="Media acumulada (sin transitorio)")
ax.plot(a.replicas, a.media_acum_con, color=AZUL, lw=1.3, ls="--", label="Media acumulada (con transitorio)")
ax.axvline(N_ACUM, color=TINTA2, ls=":", lw=1)
ax.axvline(N, color=NARANJA, lw=1.5)
ax.text(N_ACUM - 1, fin * 1.9, f"se estabiliza\nen n = {N_ACUM}", ha="right", fontsize=7.5, color=TINTA2,
        bbox=dict(fc="white", ec="none", pad=1))
ax.text(N + 1, fin * 1.9, f"réplicas usadas\nn = {N}", fontsize=7.5, color=NARANJA,
        bbox=dict(fc="white", ec="none", pad=1))
ax.set_xlabel("Número de réplicas (corridas)")
ax.set_ylabel("Espera en cola (min)")
ax.set_ylim(0, fin * 2.3)
ax.legend(fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
guardar(fig, "fig2_media_acumulada.png")

# Fig. 3: antes y después de eliminar el transitorio
c = pd.read_csv(DATA / "media_acum_tiempo.csv")
ad = pd.read_csv(DATA / "antes_despues.csv").set_index("indicador")
fig, (ax, bx) = plt.subplots(1, 2, figsize=(7.4, 3.0), gridspec_kw=dict(width_ratios=[1.6, 1]))
ax.plot(c.inicio_min, c.media_acum_con, color=AZUL, lw=1.8, label="Antes: con transitorio")
ax.plot(c.inicio_min, c.media_acum_sin, color=AQUA, lw=1.8, label="Después: sin transitorio")
ax.axhline(NIVEL, color=TINTA2, ls="--", lw=1, label="Nivel estable (Welch)")
ax.axvline(T_WARM, color=NARANJA, lw=1)
ax.set_xlabel("Minuto de la jornada")
ax.set_ylabel("Media acumulada de la espera (min)")
ax.set_title("Media acumulada en la jornada", fontsize=9, color=TINTA)
ax.legend(fontsize=7, frameon=False, loc="lower right")
ind = ["espera_min", "sistema_min"]
x = np.arange(len(ind))
for k, (col, lab, colr) in enumerate([("con_transitorio", "Antes", AZUL), ("sin_transitorio", "Después", AQUA)]):
    v = ad.loc[ind, col].values
    bx.bar(x + (k - 0.5) * 0.38, v, width=0.36, color=colr, label=lab)
    for xi, vi in zip(x, v):
        bx.text(xi + (k - 0.5) * 0.38, vi + 0.3, f"{vi:.1f}", ha="center", fontsize=7.5, color=TINTA)
bx.set_xticks(x, ["Espera en cola", "Tiempo en sistema"])
bx.set_ylabel("Minutos")
bx.set_title("Promedio de la corrida piloto", fontsize=9, color=TINTA)
bx.legend(fontsize=7, frameon=False, loc="upper left")
bx.grid(axis="x", visible=False)
fig.tight_layout()
guardar(fig, "fig3_antes_despues.png")

# Fig. 4: tiempo promedio de atención por cajero (escenario actual)
rc = pd.read_csv(DATA / "resumen_cajero.csv")
t = rc[(rc.escenario == "S0_3_filas") & (rc.metrica == "t_uso")].set_index("cajero")
fig, ax = plt.subplots(figsize=(5.6, 2.8))
cols = [AQUA if k == t.media.idxmin() else NARANJA if k == t.media.idxmax() else AZUL for k in t.index]
ax.bar([f"Cajero {k}" for k in t.index], t.media, color=cols, width=0.55,
       yerr=[t.media - t.ic_inf, t.ic_sup - t.media], error_kw=dict(ecolor=TINTA2, lw=1, capsize=3))
for i, (m, hi) in enumerate(zip(t.media, t.ic_sup)):
    ax.text(i, hi + 0.08, f"{m:.2f} min", ha="center", fontsize=8, color=TINTA)
ax.set_ylim(0, t.ic_sup.max() * 1.2)
ax.set_ylabel(f"Tiempo de atención (min)\nIC 95 %, {N} réplicas")
ax.grid(axis="x", visible=False)
guardar(fig, "fig4_tiempo_cajero.png")

# Fig. 5: promedio de usuarios de cada tipo por cajero
u = pd.read_csv(DATA / "usuarios_tipo_cajero.csv", index_col=0)
u = u.drop(index="Total")[pq.TIPOS]
fig, ax = plt.subplots(figsize=(6.4, 2.9))
x = np.arange(len(u))
for k, tp in enumerate(pq.TIPOS):
    xs = x + (k - 1.5) * 0.2
    ax.bar(xs, u[tp], width=0.19, color=COL_TIPO[tp], label=tp)
    for xi, v in zip(xs, u[tp]):
        ax.text(xi, v + 0.5, f"{v:.1f}", ha="center", fontsize=6.5, color=TINTA)
ax.set_xticks(x, [f"Cajero {k}" for k in u.index])
ax.set_ylabel("Usuarios promedio por réplica\n(estado estable)")
ax.legend(fontsize=7, frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.15))
ax.grid(axis="x", visible=False)
guardar(fig, "fig5_usuarios_tipo.png")

# Fig. 6: espera por escenario y criterio de decisión
d = pd.read_csv(DATA / "decision.csv").set_index("escenario").loc[ESC]
fig, (ax, bx) = plt.subplots(1, 2, figsize=(7.6, 2.9), sharey=True)
y = np.arange(len(ESC))[::-1]
cols = [AQUA if c else NARANJA for c in d.cumple]
ax.barh(y, d.espera, height=0.55, color=cols, xerr=[d.espera - d.ic_inf, d.ic_sup - d.espera],
        error_kw=dict(ecolor=TINTA2, lw=1, capsize=3))
xr = d.ic_sup.max() * 1.06
for yi, m in zip(y, d.espera):
    ax.text(xr, yi, f"{m:.1f} min", va="center", fontsize=8, color=TINTA)
ax.axvline(5, color=TINTA2, ls="--", lw=1)
ax.set_xlabel("Espera promedio en cola (min)")
ax.set_yticks(y, [pq.DESCRIPCION[e] for e in ESC])
ax.set_xlim(0, xr * 1.25)
bx.barh(y, d.p_espera_10 * 100, height=0.55, color=cols)
for yi, v in zip(y, d.p_espera_10 * 100):
    bx.text(v + 1, yi, f"{v:.1f} %", va="center", fontsize=8, color=TINTA)
bx.axvline(10, color=TINTA2, ls="--", lw=1)
bx.set_xlabel("Usuarios que esperan más de 10 min (%)")
bx.set_xlim(0, d.p_espera_10.max() * 120)
for z in (ax, bx):
    z.grid(axis="y", visible=False)
fig.tight_layout()
guardar(fig, "fig6_escenarios.png")

# Fig. 7: proceso de verificación, calibración y validación
fig, ax = plt.subplots(figsize=(7.4, 3.6))
ax.set_xlim(0, 10)
ax.set_ylim(0, 5)
ax.axis("off")


def caja(x, y, w, h, texto, color, tit):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.12",
                                fc=color, ec="none", alpha=0.18))
    ax.text(x + w / 2, y + h - 0.2, tit, ha="center", va="top", fontsize=8.5, weight="bold", color=TINTA)
    ax.text(x + w / 2, y + h / 2 - 0.15, texto, ha="center", va="center", fontsize=7, color=TINTA2,
            linespacing=1.35)


def flecha(x0, y0, x1, y1, txt=None, dx=0.0, ha="center"):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color=TINTA2, lw=1.1))
    if txt:
        ax.text((x0 + x1) / 2 + dx, (y0 + y1) / 2 + (0 if dx else 0.1), txt, ha=ha,
                va="center" if dx else "bottom", fontsize=6.6, color=TINTA2)


caja(0.1, 3.3, 2.3, 1.5, "Supercentro: 3 cajeros,\ncolas M/M/1, 4 tipos\nde usuario", GRIS, "Sistema real")
caja(3.8, 3.3, 2.4, 1.5, "Supuestos, tabla de\nmedias, reparto 55 %\nlento / muy lento", AZUL, "Modelo conceptual")
caja(7.6, 3.3, 2.3, 1.5, "parqueadero.py\nSimPy, 1 recurso\npor cajero", AZUL, "Modelo simulado")
caja(7.6, 0.2, 2.3, 1.9, "Pruebas (pytest), traza\nde eventos, ley de Little,\nconservación de usuarios", NARANJA, "Verificación")
caja(3.8, 0.2, 2.4, 1.9, "Medias y proporciones\nsimuladas vs. tabla;\nhistogramas vs. exponencial", AQUA, "Calibración")
caja(0.1, 0.2, 2.3, 1.9, "Wq, ρ y usuarios/día\nvs. P-K y Kingman;\nsensibilidad", MORADO, "Validación")
flecha(2.45, 4.05, 3.75, 4.05, "abstracción")
flecha(6.25, 4.05, 7.55, 4.05, "programación")
flecha(8.75, 3.25, 8.75, 2.15, "¿el código hace lo\nque dice el modelo?", dx=-0.12, ha="right")
flecha(7.55, 1.15, 6.25, 1.15, "código\ncorrecto")
flecha(3.75, 1.15, 2.45, 1.15, "entradas\najustadas")
flecha(1.25, 2.15, 1.25, 3.25, "¿representa al\nsistema real?", dx=0.12, ha="left")
ax.annotate("", xy=(4.6, 3.25), xytext=(2.45, 2.05),
            arrowprops=dict(arrowstyle="-|>", color=NARANJA, lw=1, ls="--", connectionstyle="arc3,rad=-0.2"))
ax.text(4.3, 2.45,"si no: revisar\nsupuestos", fontsize=6.8, color=NARANJA, ha="center")
guardar(fig, "fig7_proceso_vv.png")

# Fig. 8: calibración, tiempo de uso simulado vs. exponencial de la tabla
mu = pd.read_csv(DATA / "muestra_usos.csv")
fig, axs = plt.subplots(1, 4, figsize=(8.0, 2.4))
for ax, tp in zip(axs, pq.TIPOS):
    v = mu[mu.tipo == tp].uso
    m = pq.TABLA[tp][0]
    xs = np.linspace(0, m * 5, 200)
    ax.hist(v, bins=np.linspace(0, m * 5, 30), density=True, color=COL_TIPO[tp], alpha=0.55)
    ax.plot(xs, np.exp(-xs / m) / m, color=TINTA, lw=1.2)
    ax.set_title(f"{tp}: media {v.mean():.2f} (tabla {m:.0f})", fontsize=7.5, color=TINTA)
    ax.set_xlabel("Uso del cajero (min)", fontsize=7.5)
    ax.tick_params(labelsize=7)
axs[0].set_ylabel("Densidad", fontsize=7.5)
fig.tight_layout()
guardar(fig, "fig8_calibracion.png")

# Fig. 9: validación contra la teoría
v = pd.read_csv(DATA / "validacion.csv").set_index("indicador")["valor"]
fig, (ax, bx) = plt.subplots(1, 2, figsize=(7.2, 2.7), gridspec_kw=dict(width_ratios=[1.5, 1]))
lab = ["Kingman\nG/G/1", "Pollaczek-\nKhinchine M/G/1", "Simulación\n(estado estable)"]
vals = [v["Wq aproximación de Kingman G/G/1 (min)"], v["Wq fórmula de Pollaczek-Khinchine M/G/1 (min)"],
        v["Wq simulada, estado estable (min)"]]
ax.bar(lab, vals, color=[GRIS, GRIS, AZUL], width=0.55)
for i, val in enumerate(vals):
    ax.text(i, val + 0.3, f"{val:.1f} min", ha="center", fontsize=8, color=TINTA)
ax.set_ylabel("Espera en cola por cajero (min)")
ax.set_ylim(0, max(vals) * 1.2)
ax.grid(axis="x", visible=False)
lab2 = ["ρ teórico", "Utilización\nsimulada"]
vals2 = [v["ρ por cajero, teórico"], v["Utilización por cajero, simulada"]]
bx.bar(lab2, vals2, color=[GRIS, AZUL], width=0.5)
for i, val in enumerate(vals2):
    bx.text(i, val + 0.02, f"{val:.2f}", ha="center", fontsize=8, color=TINTA)
bx.set_ylim(0, 1)
bx.set_ylabel("Ocupación del cajero")
bx.grid(axis="x", visible=False)
fig.tight_layout()
guardar(fig, "fig9_validacion.png")

# Fig. 10: sensibilidad al reparto lento / muy lento
s = pd.read_csv(DATA / "sensibilidad.csv")
rep = list(dict.fromkeys(s.reparto))
esc_s = list(dict.fromkeys(s.escenario))
fig, ax = plt.subplots(figsize=(6.4, 2.8))
x = np.arange(len(rep))
for k, (e, col) in enumerate(zip(esc_s, [NARANJA, AZUL, AQUA])):
    h = s[s.escenario == e].set_index("reparto").loc[rep, "espera"]
    xs = x + (k - 1) * 0.26
    ax.bar(xs, h, width=0.24, color=col, label=pq.DESCRIPCION[e])
    for xi, val in zip(xs, h):
        ax.text(xi, val + 0.3, f"{val:.1f}", ha="center", fontsize=7, color=TINTA)
ax.axhline(5, color=TINTA2, ls="--", lw=1)
ax.set_xticks(x, [r.replace(" / ", "\n") for r in rep], fontsize=8)
ax.set_ylabel("Espera promedio en cola (min)")
ax.legend(fontsize=7, frameon=False)
ax.grid(axis="x", visible=False)
guardar(fig, "fig10_sensibilidad.png")

print("Figuras en", FIGS)
