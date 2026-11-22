"""Corre las réplicas de todos los escenarios y escribe los CSV de resultados en data/.

Uso:  python run_experiments.py [--replicas 10]
La réplica r usa la semilla r en todos los escenarios (números aleatorios comunes).
"""
from __future__ import annotations

import argparse
import platform
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import simpy
from scipy import stats

import banco

DATA = Path(__file__).parent / "data"
UMBRAL_ESPERA = 5.0  # minutos: espera promedio máxima aceptable en cualquier criterio
EPS_ESPERA = 0.5     # minutos: semiancho deseado del IC 95 % de la espera promedio
EPS_USUARIOS = 10.0  # usuarios: semiancho deseado del IC 95 % de los usuarios por día


def ic95(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    m = x.mean()
    s = x.std(ddof=1) if n > 1 else 0.0
    h = stats.t.ppf(0.975, n - 1) * s / np.sqrt(n) if n > 1 else 0.0
    return m, s, m - h, m + h


def resumir(df, por, valor):
    filas = []
    for clave, g in df.groupby(por, sort=False):
        m, s, lo, hi = ic95(g[valor])
        clave = clave if isinstance(clave, tuple) else (clave,)
        filas.append({**dict(zip(por, clave)), "media": m, "de": s, "ic_inf": lo, "ic_sup": hi, "n": len(g)})
    return pd.DataFrame(filas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replicas", type=int, default=10)
    args = ap.parse_args()
    DATA.mkdir(exist_ok=True)

    regs = []
    for esc in banco.ESCENARIOS:
        for r in range(1, args.replicas + 1):
            regs += [asdict(x) for x in banco.simular(esc, semilla=r, replica=r)]
    df = pd.DataFrame(regs)
    df["espera"] = df["inicio"] - df["llegada"]
    df["servicio"] = df["fin"] - df["inicio"]
    df["sistema"] = df["fin"] - df["llegada"]
    df["tipo_usuario"] = df["operacion"] + " - " + df["tipo"]
    df.round(4).to_csv(DATA / "registros.csv", index=False)

    # --- Por caja y réplica
    def por_caja_rep(g):
        horizonte = max(g["fin"].max(), banco.JORNADA)  # la caja trabaja hasta vaciar su fila
        lam = len(g) / horizonte  # tasa de llegada observada a esta caja (usuarios/min)
        return pd.Series({
            "atendidos": len(g),
            "t_atencion": g["servicio"].mean(),
            "t_sistema": g["sistema"].mean(),
            "espera": g["espera"].mean(),
            "espera_max": g["espera"].max(),
            "utilizacion": g["servicio"].sum() / horizonte,  # ρ observado
            "lq": lam * g["espera"].mean(),  # ley de Little: Lq = λ·Wq
        })
    caja = df.groupby(["escenario", "replica", "caja"]).apply(por_caja_rep, include_groups=False).reset_index()
    caja.round(4).to_csv(DATA / "por_caja_replica.csv", index=False)
    res_caja = pd.concat([resumir(caja, ["escenario", "caja"], v).assign(metrica=v)
                          for v in ["atendidos", "t_atencion", "t_sistema", "espera", "utilizacion", "lq"]])
    res_caja.round(4).to_csv(DATA / "resumen_caja.csv", index=False)

    # --- Usuarios por tipo y réplica (no depende del escenario: mismas llegadas)
    base = df[df["escenario"] == "E0_3mixtas"]
    orden = [f"{o} - {t}" for o, t in banco.TIPOS]
    conteo = base.pivot_table(index="replica", columns="tipo_usuario", values="usuario",
                              aggfunc="count", fill_value=0)[orden]
    conteo["Total"] = conteo.sum(axis=1)
    conteo.to_csv(DATA / "usuarios_tipo_replica.csv")
    # Usuarios por tipo en cada caja (promedio de las réplicas) para cada escenario
    tc = (df.groupby(["escenario", "replica", "caja", "tipo_usuario"]).size()
            .unstack("tipo_usuario", fill_value=0).reindex(columns=orden, fill_value=0))
    tc = tc.groupby(["escenario", "caja"]).mean()
    tc["Total"] = tc.sum(axis=1)
    tc.round(2).to_csv(DATA / "usuarios_tipo_caja.csv")

    # --- Esperas promedio por criterio (escenario × criterio), una cifra por réplica
    criterios = []
    for (esc, r), g in df.groupby(["escenario", "replica"]):
        criterios.append({"escenario": esc, "replica": r, "criterio": "General", "espera": g["espera"].mean()})
        for op, h in g.groupby("operacion"):
            criterios.append({"escenario": esc, "replica": r, "criterio": f"Operación: {op}", "espera": h["espera"].mean()})
        for tu, h in g.groupby("tipo_usuario"):
            criterios.append({"escenario": esc, "replica": r, "criterio": f"Tipo: {tu}", "espera": h["espera"].mean()})
        for c, h in g.groupby("caja"):
            criterios.append({"escenario": esc, "replica": r, "criterio": f"Caja {c}", "espera": h["espera"].mean()})
    crit = pd.DataFrame(criterios)
    crit.round(4).to_csv(DATA / "espera_criterio_replica.csv", index=False)
    res_crit = resumir(crit, ["escenario", "criterio"], "espera")
    res_crit["supera_umbral"] = res_crit["media"] > UMBRAL_ESPERA
    res_crit.round(4).to_csv(DATA / "resumen_espera_criterio.csv", index=False)

    # --- Comparaciones pareadas (misma réplica = mismos usuarios)
    gen = crit[crit["criterio"] == "General"].pivot(index="replica", columns="escenario", values="espera")
    pares = [("E1_1R_2P", "E2_2R_1P"), ("E0_3mixtas", "E2_2R_1P"), ("E0_3mixtas", "E3_4mixtas"),
             ("E2_2R_1P", "E4_2R_2P"), ("E0_3mixtas", "E4_2R_2P")]
    comp = []
    for a, b in pares:
        d = gen[a] - gen[b]
        m, s, lo, hi = ic95(d)
        t, p = stats.ttest_rel(gen[a], gen[b])
        comp.append({"a": a, "b": b, "dif_media": m, "ic_inf": lo, "ic_sup": hi, "t": t, "p": p})
    pd.DataFrame(comp).round(5).to_csv(DATA / "comparaciones.csv", index=False)

    # --- Validación contra la teoría
    teo = banco.valores_teoricos()
    n_val = [len(banco.generar_usuarios(s)) for s in range(10_001, 12_001)]
    val = [
        ("Usuarios por día (teórico)", teo["usuarios_dia"]),
        ("Usuarios por día (2000 jornadas simuladas)", float(np.mean(n_val))),
        ("Usuarios por día (10 réplicas)", float(conteo["Total"].mean())),
        ("Proporción de retiros (10 réplicas)", float((base["operacion"] == "Retiro").mean())),
        ("Servicio medio retiro E[S] teórico", teo["Retiro"]["ES"]),
        ("Servicio medio retiro simulado", float(base.loc[base.operacion == "Retiro", "servicio"].mean())),
        ("Servicio medio pago E[S] teórico", teo["Pago"]["ES"]),
        ("Servicio medio pago simulado", float(base.loc[base.operacion == "Pago", "servicio"].mean())),
        ("Carga retiros (Erlang)", teo["Retiro"]["carga"]),
        ("Carga pagos (Erlang)", teo["Pago"]["carga"]),
    ]
    pd.DataFrame(val, columns=["indicador", "valor"]).round(4).to_csv(DATA / "validacion.csv", index=False)

    # --- Robustez: 100 réplicas adicionales (semillas 1001-1100) para la decisión de asignación
    rob = []
    for esc in banco.ESCENARIOS:
        for s in range(1001, 1101):
            g = pd.DataFrame([asdict(x) for x in banco.simular(esc, semilla=s)])
            g["espera"] = g["inicio"] - g["llegada"]
            fila = {"escenario": esc, "semilla": s, "General": g["espera"].mean()}
            for op in banco.OPERACIONES:
                fila[op] = g.loc[g.operacion == op, "espera"].mean()
            rob.append(fila)
    rob = pd.DataFrame(rob)
    rob.round(4).to_csv(DATA / "robustez_replicas.csv", index=False)
    filas = []
    for esc, g in rob.groupby("escenario", sort=False):
        for v in ["General", "Retiro", "Pago"]:
            m, s, lo, hi = ic95(g[v])
            filas.append({"escenario": esc, "criterio": v, "media": m, "ic_inf": lo, "ic_sup": hi, "n": len(g)})
    piv = rob.pivot(index="semilla", columns="escenario", values="General")
    t, p = stats.ttest_rel(piv["E1_1R_2P"], piv["E2_2R_1P"])
    d = piv["E1_1R_2P"] - piv["E2_2R_1P"]
    m, s, lo, hi = ic95(d)
    filas.append({"escenario": "E1-E2 (pareada)", "criterio": "General", "media": m, "ic_inf": lo,
                  "ic_sup": hi, "n": len(d), "t": t, "p": p})
    pd.DataFrame(filas).round(5).to_csv(DATA / "robustez.csv", index=False)

    # --- Número de réplicas necesarias: menor n con t(0.975, n-1)·s/√n <= ε (s de la muestra piloto)
    def n_necesario(s, eps):
        n = 2
        while stats.t.ppf(0.975, n - 1) * s / np.sqrt(n) > eps:
            n += 1
        return n

    nrep = []
    for esc in banco.ESCENARIOS:
        for crit_nom, col in [("Espera general", "General"), ("Espera retiros", "Retiro"), ("Espera pagos", "Pago")]:
            c10 = {"General": "General", "Retiro": "Operación: Retiro", "Pago": "Operación: Pago"}[col]
            s10 = crit[(crit.escenario == esc) & (crit.criterio == c10)]["espera"].std(ddof=1)
            s100 = rob.loc[rob.escenario == esc, col].std(ddof=1)
            nrep.append({"escenario": esc, "indicador": crit_nom, "precision_min": EPS_ESPERA,
                         "de_10": s10, "n_req_10": n_necesario(s10, EPS_ESPERA),
                         "de_100": s100, "n_req_100": n_necesario(s100, EPS_ESPERA)})
    s_users = conteo["Total"].std(ddof=1)
    nrep.append({"escenario": "Todos", "indicador": "Usuarios por día", "precision_min": EPS_USUARIOS,
                 "de_10": s_users, "n_req_10": n_necesario(s_users, EPS_USUARIOS),
                 "de_100": np.nan, "n_req_100": np.nan})
    nrep = pd.DataFrame(nrep)
    nrep.round(4).to_csv(DATA / "replicas_necesarias.csv", index=False)

    # --- Libro de Excel con las tablas principales (entregable que pide la guía)
    with pd.ExcelWriter(DATA / "resultados_simulacion_banco.xlsx") as xl:
        df.round(4).to_excel(xl, sheet_name="registros", index=False)
        caja.round(4).to_excel(xl, sheet_name="por_caja_replica", index=False)
        res_caja.round(4).to_excel(xl, sheet_name="resumen_caja", index=False)
        conteo.to_excel(xl, sheet_name="usuarios_tipo_replica")
        tc.round(2).to_excel(xl, sheet_name="usuarios_tipo_caja")
        res_crit.round(4).to_excel(xl, sheet_name="espera_criterios", index=False)
        pd.DataFrame(comp).round(5).to_excel(xl, sheet_name="comparaciones", index=False)
        pd.DataFrame(filas).round(5).to_excel(xl, sheet_name="robustez_100", index=False)
        nrep.round(4).to_excel(xl, sheet_name="replicas_necesarias", index=False)
        pd.DataFrame(val, columns=["indicador", "valor"]).round(4).to_excel(xl, sheet_name="validacion", index=False)

    (DATA / "entorno.txt").write_text(
        f"python {sys.version.split()[0]} ({platform.system()})\nsimpy {simpy.__version__}\n"
        f"numpy {np.__version__}\npandas {pd.__version__}\nscipy {scipy.__version__}\n"
        f"replicas {args.replicas}\n", encoding="utf8")
    print(gen.mean().round(3).to_string())


if __name__ == "__main__":
    main()
