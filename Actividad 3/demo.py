"""Demostración en consola: simula los escenarios y responde los 5 puntos del laboratorio.

Uso:  python demo.py   (unos segundos; usa 10 réplicas por escenario)
"""
import sys
from dataclasses import asdict

import pandas as pd

import banco

sys.stdout.reconfigure(encoding="utf-8")  # tildes correctas en la consola de Windows
REPLICAS = 10
UMBRAL = 5.0  # minutos de espera promedio aceptables


def linea(titulo):
    print("\n" + "=" * 78 + f"\n{titulo}\n" + "=" * 78)


# Simular todos los escenarios con las mismas semillas (números aleatorios comunes)
print(f"Simulando {len(banco.ESCENARIOS)} escenarios x {REPLICAS} réplicas de 8 horas...")
df = pd.DataFrame([asdict(r) for e in banco.ESCENARIOS for s in range(1, REPLICAS + 1)
                   for r in banco.simular(e, semilla=s, replica=s)])
df["espera"] = df["inicio"] - df["llegada"]
df["servicio"] = df["fin"] - df["inicio"]
df["tipo_usuario"] = df["operacion"] + " - " + df["tipo"]
actual = df[df.escenario == "E0_3mixtas"]

linea("PUNTO 1. Tiempo promedio de atención por cajero (situación actual)")
t = actual.groupby(["replica", "caja"])["servicio"].mean().groupby("caja").mean()
for caja, v in t.items():
    print(f"  Caja {caja}: {v:.2f} min")
print(f"  -> Mayor: caja {t.idxmax()} ({t.max():.2f} min) | Menor: caja {t.idxmin()} ({t.min():.2f} min)")

linea("PUNTO 2. Promedio de usuarios de cada tipo en el total de cajeros")
conteo = actual.groupby(["replica", "tipo_usuario"]).size().unstack(fill_value=0)
orden = [f"{o} - {k}" for o, k in banco.TIPOS]
for tu in orden:
    print(f"  {tu:<20} {conteo[tu].mean():6.1f} usuarios/día")
print(f"  {'Total':<20} {conteo.sum(axis=1).mean():6.1f} usuarios/día")

linea("PUNTO 3. Total de usuarios de cada tipo en cada réplica")
tabla = conteo[orden].copy()
tabla.columns = [c.replace("Retiro - ", "R ").replace("Pago - ", "P ") for c in tabla.columns]
tabla["Total"] = tabla.sum(axis=1)
print(tabla.to_string())
print(f"  -> Réplica con menos usuarios: {tabla['Total'].idxmin()} ({tabla['Total'].min()} usuarios)")

linea(f"PUNTO 4. ¿Hace falta una caja nueva? (meta: espera <= {UMBRAL:.0f} min en todo criterio)")
for esc, g in df.groupby("escenario", sort=False):
    general = g.groupby("replica")["espera"].mean().mean()
    criterios = pd.concat([g.groupby(["replica", "operacion"])["espera"].mean().groupby("operacion").mean(),
                           g.groupby(["replica", "tipo_usuario"])["espera"].mean().groupby("tipo_usuario").mean()])
    peor = criterios.max()
    estado = "CUMPLE" if peor <= UMBRAL else "NO CUMPLE"
    print(f"  {banco.DESCRIPCION[esc]:<45} general {general:5.2f} | peor {peor:5.2f} min | {estado}")
print("  -> Con las 3 cajas mixtas no hace falta caja nueva; sí hace falta si se especializan.")

linea("PUNTO 5. ¿Cuántas cajas exclusivas para pagos y para retiros?")
for esc in ["E1_1R_2P", "E2_2R_1P"]:
    g = df[df.escenario == esc]
    op = g.groupby(["replica", "operacion"])["espera"].mean().groupby("operacion").mean()
    gen = g.groupby("replica")["espera"].mean().mean()
    print(f"  {banco.DESCRIPCION[esc]:<33} general {gen:5.2f} | retiros {op['Retiro']:5.2f} | pagos {op['Pago']:5.2f} min")
print("  -> Conviene 2 cajas de retiros y 1 de pagos (la caja saturada queda para el grupo menor).")
print("  -> Recomendación final: mantener las 3 cajas mixtas (menor espera de todas).")
