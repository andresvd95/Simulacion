"""Demostración en consola: estado estable y respuestas a los puntos del enunciado.

Uso:  python demo.py   (unos 30 s; usa 30 réplicas por escenario y el fin del transitorio de
                         data/estado_estable.csv si ya se ejecutó run_experiments.py, o 220 min)
"""
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

import parqueadero as pq

sys.stdout.reconfigure(encoding="utf-8")  # tildes correctas en la consola de Windows
REPLICAS = 30
META_ESPERA, META_P10 = 5.0, 0.10
f = Path(__file__).parent / "data" / "estado_estable.csv"
T_WARM = float(pd.read_csv(f, index_col=0)["valor"]["t_transitorio_min"]) if f.exists() else 220.0


def linea(titulo):
    print("\n" + "=" * 78 + f"\n{titulo}\n" + "=" * 78)


print(f"Simulando {len(pq.ESCENARIOS)} escenarios x {REPLICAS} réplicas de {pq.HORIZONTE / 60:.0f} h...")
df = pd.DataFrame([asdict(r) for e in pq.ESCENARIOS for s in range(1, REPLICAS + 1)
                   for r in pq.simular(e, semilla=s, replica=s)])
df["espera"] = df["inicio"] - df["llegada"]
df["uso"] = df["fin"] - df["inicio"]

linea("ESTADO ESTABLE. Media de la espera por hora de la jornada (escenario actual)")
act_todo = df[df.escenario == "S0_3_filas"]
tramos = act_todo.groupby(pd.cut(act_todo.llegada, np.arange(0, pq.HORIZONTE + 60, 60)), observed=True)["espera"].mean()
for k, v in tramos.items():
    print(f"  {k.left:4.0f}-{k.right:4.0f} min: {v:5.2f} min {'#' * int(v)}")
print(f"  -> La espera sube y luego se estabiliza: se descartan los primeros {T_WARM:.0f} min (transitorio).")

est = df[df.llegada >= T_WARM]
act = est[est.escenario == "S0_3_filas"]

linea("PUNTO 1. Tiempo promedio de atención por cajero (3 cajeros actuales)")
t = act.groupby(["replica", "cajero"])["uso"].mean().groupby("cajero").mean()
for c, v in t.items():
    print(f"  Cajero {c}: {v:.2f} min")
print(f"  -> Máximo: cajero {t.idxmax()} ({t.max():.2f} min) | Mínimo: cajero {t.idxmin()} ({t.min():.2f} min)")

linea("PUNTO 2. Promedio de usuarios de cada tipo en el total de cajeros")
conteo = act.groupby(["replica", "tipo"]).size().unstack(fill_value=0)[pq.TIPOS]
for tp in pq.TIPOS:
    print(f"  {tp:<10} {conteo[tp].mean():6.1f} usuarios por réplica (estado estable)")
print(f"  {'Total':<10} {conteo.sum(axis=1).mean():6.1f}")

linea(f"PUNTO 3. ¿Bastan 3 cajeros? (criterio: espera <= {META_ESPERA:.0f} min y <= {META_P10:.0%} espera > 10 min)")
for e, g in est.groupby("escenario", sort=False):
    w = g.groupby("replica")["espera"].mean().mean()
    p10 = g.groupby("replica")["espera"].apply(lambda x: (x > 10).mean()).mean()
    ok = "CUMPLE" if w <= META_ESPERA and p10 <= META_P10 else "NO CUMPLE"
    print(f"  {pq.DESCRIPCION[e]:<42} espera {w:5.2f} min | >10 min {p10:6.1%} | {ok}")
print("  -> Con 3 filas independientes NO bastan. Etapa 1: fila única con los 3 cajeros (sin inversión).")
print("  -> Etapa 2: instalar un 4.º cajero con fila única, la única opción que cumple todo el criterio.")

linea("PUNTO 4. Validación rápida contra la teoría")
teo = pq.valores_teoricos()
print(f"  ρ por cajero teórico {teo['rho']:.3f} | Wq Pollaczek-Khinchine {teo['wq_pk']:.1f} min | "
      f"Wq simulada {act.groupby('replica')['espera'].mean().mean():.1f} min")
