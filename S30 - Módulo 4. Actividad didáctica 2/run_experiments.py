"""Experimentos del problema de parqueaderos. Escribe todos los resultados en data/.

Pasos:
  1. Corrida piloto (100 réplicas del escenario actual) para analizar el estado estable:
     a) método de Welch (media móvil de la espera por intervalo de tiempo) -> fin del transitorio;
     b) técnica de la media acumulada sobre las réplicas -> número de corridas necesarias.
  2. Corrida de todos los escenarios con ese número de réplicas, eliminando el transitorio.
  3. Estadísticas de los puntos del enunciado, criterio de decisión y validación.

Uso:  python run_experiments.py
"""
from __future__ import annotations

import platform
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import simpy
from scipy import stats

import parqueadero as pq

DATA = Path(__file__).parent / "data"
R_PILOTO = 100          # réplicas de la corrida piloto
INTERVALO = 10.0        # minutos por intervalo para el método de Welch
VENTANA = 6             # semiancho de la media móvil (intervalos a cada lado)
TOL_TRANSITORIO = 0.10  # la media móvil debe llegar al 90 % del nivel estable
TOL_REPLICAS = 0.05     # la media acumulada debe quedar dentro de ±5 % de su valor final
PRECISION = 0.10        # semiancho relativo aceptable del IC 95 % (fórmula clásica)
META_ESPERA = 5.0       # criterio: espera promedio máxima aceptable (min)
META_P10 = 0.10         # criterio: máximo 10 % de usuarios esperando más de 10 min


def ic95(x):
    x = np.asarray(x, dtype=float)
    m, s, n = x.mean(), x.std(ddof=1), len(x)
    h = stats.t.ppf(0.975, n - 1) * s / np.sqrt(n)
    return m, s, m - h, m + h


def a_tabla(regs):
    df = pd.DataFrame([asdict(r) for r in regs])
    df["espera"] = df["inicio"] - df["llegada"]
    df["uso"] = df["fin"] - df["inicio"]
    df["sistema"] = df["fin"] - df["llegada"]
    return df


def media_movil(y, w):
    """Media móvil de Welch: ventana centrada de 2w+1 puntos (más corta en los extremos)."""
    out = np.empty(len(y))
    for i in range(len(y)):
        k = min(i, w, len(y) - 1 - i)
        out[i] = y[i - k:i + k + 1].mean()
    return out


def detectar_transitorio(inicio, mm, tol=TOL_TRANSITORIO):
    """Algoritmo: nivel estable = media de la segunda mitad de la curva suavizada;
    el transitorio termina en el primer intervalo donde la media móvil llega al (1-tol) del nivel."""
    nivel = mm[len(mm) // 2:].mean()
    idx = int(np.argmax(mm >= (1 - tol) * nivel))
    return float(inicio[idx]), float(nivel)


def n_media_acumulada(serie, tol=TOL_REPLICAS):
    """Menor n a partir del cual la media acumulada ya no sale de ±tol de su valor final."""
    final = serie[-1]
    fuera = np.abs(serie - final) > tol * final
    return int(np.max(np.nonzero(fuera)[0]) + 2) if fuera.any() else 1


def n_formula(x, precision=PRECISION):
    """Menor n con t(0.975, n-1)·s/√n <= precision·media (s y media de la corrida piloto)."""
    s, mu = np.std(x, ddof=1), np.mean(x)
    n = 2
    while stats.t.ppf(0.975, n - 1) * s / np.sqrt(n) > precision * mu:
        n += 1
    return n


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    DATA.mkdir(exist_ok=True)

    # ---------------------------------------------------------------- 1. corrida piloto
    piloto = pd.concat([a_tabla(pq.simular("S0_3_filas", s)) for s in range(1, R_PILOTO + 1)])
    n_int = int(pq.HORIZONTE // INTERVALO)
    piloto["intervalo"] = np.minimum((piloto["llegada"] // INTERVALO).astype(int), n_int - 1)
    por_int = (piloto.groupby(["replica", "intervalo"])["espera"].mean()
               .unstack().reindex(columns=range(n_int)))
    welch = pd.DataFrame({"inicio_min": np.arange(n_int) * INTERVALO,
                          "espera_media": por_int.mean(axis=0).values})
    welch["media_movil"] = media_movil(welch["espera_media"].values, VENTANA)
    t_warm, nivel = detectar_transitorio(welch["inicio_min"].values, welch["media_movil"].values)
    welch["nivel_estable"] = nivel
    welch.round(4).to_csv(DATA / "welch.csv", index=False)

    # media acumulada de la espera por réplica (con y sin transitorio)
    diaria_con = piloto.groupby("replica")["espera"].mean()
    diaria_sin = piloto[piloto.llegada >= t_warm].groupby("replica")["espera"].mean()
    acum = pd.DataFrame({"replicas": np.arange(1, R_PILOTO + 1),
                         "espera_replica_con": diaria_con.values,
                         "espera_replica_sin": diaria_sin.values})
    acum["media_acum_con"] = acum["espera_replica_con"].expanding().mean()
    acum["media_acum_sin"] = acum["espera_replica_sin"].expanding().mean()
    acum.round(4).to_csv(DATA / "media_acumulada.csv", index=False)
    n_acum = n_media_acumulada(acum["media_acum_sin"].values)
    n_form = n_formula(diaria_sin.values)
    N = max(n_acum, n_form)

    # antes y después de eliminar el transitorio (corrida piloto del escenario actual)
    def resumen(d):
        return {"espera_min": d["espera"].mean(), "uso_min": d["uso"].mean(),
                "sistema_min": d["sistema"].mean(), "espera_p95_min": d["espera"].quantile(0.95),
                "usuarios_por_replica": len(d) / R_PILOTO}
    antes, despues = resumen(piloto), resumen(piloto[piloto.llegada >= t_warm])
    pd.DataFrame([{"indicador": k, "con_transitorio": antes[k], "sin_transitorio": despues[k]}
                  for k in antes]).round(4).to_csv(DATA / "antes_despues.csv", index=False)
    # media acumulada de la espera a lo largo de la jornada (promedio de las réplicas)
    curva = pd.DataFrame({"inicio_min": welch["inicio_min"],
                          "media_acum_con": welch["espera_media"].expanding().mean()})
    sin = welch[welch.inicio_min >= t_warm]["espera_media"].expanding().mean()
    curva["media_acum_sin"] = sin.reindex(curva.index)
    curva.round(4).to_csv(DATA / "media_acum_tiempo.csv", index=False)

    params = {"t_transitorio_min": t_warm, "nivel_estable_min": nivel,
              "n_media_acumulada": n_acum, "n_formula_ic": n_form, "replicas_usadas": N,
              "r_piloto": R_PILOTO, "intervalo_min": INTERVALO, "ventana_welch": VENTANA,
              "tol_transitorio": TOL_TRANSITORIO, "tol_replicas": TOL_REPLICAS, "precision_ic": PRECISION}
    pd.Series(params).to_csv(DATA / "estado_estable.csv", header=["valor"], index_label="parametro")

    # ---------------------------------------------------------------- 2. escenarios
    todo = pd.concat([a_tabla(pq.simular(e, s, replica=s)) for e in pq.ESCENARIOS
                      for s in range(1, N + 1)])
    est = todo[todo.llegada >= t_warm].copy()   # se elimina el transitorio en todos los escenarios
    est.drop(columns="usuario").round(4).to_csv(DATA / "registros_estables.csv", index=False)

    # Punto 1: tiempo promedio de atención por cajero
    filas = []
    for (e, r, k), g in est.groupby(["escenario", "replica", "cajero"], sort=False):
        horiz = max(pq.HORIZONTE, g["fin"].max()) - t_warm
        filas.append({"escenario": e, "replica": r, "cajero": k, "usuarios": len(g),
                      "t_uso": g["uso"].mean(), "t_sistema": g["sistema"].mean(), "espera": g["espera"].mean(),
                      "utilizacion": g["uso"].sum() / horiz, "lq": g["espera"].sum() / horiz})
    caj = pd.DataFrame(filas)
    caj.round(4).to_csv(DATA / "por_cajero_replica.csv", index=False)
    filas = []
    for (e, k), g in caj.groupby(["escenario", "cajero"], sort=False):
        for v in ["usuarios", "t_uso", "t_sistema", "espera", "utilizacion", "lq"]:
            m, sd, lo, hi = ic95(g[v])
            filas.append({"escenario": e, "cajero": k, "metrica": v, "media": m, "de": sd,
                          "ic_inf": lo, "ic_sup": hi})
    res_caj = pd.DataFrame(filas)
    res_caj.round(4).to_csv(DATA / "resumen_cajero.csv", index=False)
    a0 = caj[caj.escenario == "S0_3_filas"]
    anova = stats.f_oneway(*[g["t_uso"].values for _, g in a0.groupby("cajero")])
    pd.Series({"F": anova.statistic, "p": anova.pvalue}).to_csv(DATA / "anova_cajeros.csv", header=["valor"])

    # Punto 2: promedio de usuarios de cada tipo por cajero y en total (escenario actual)
    act = est[est.escenario == "S0_3_filas"]
    tc = (act.groupby(["replica", "cajero", "tipo"]).size().unstack(fill_value=0)
          .reindex(columns=pq.TIPOS, fill_value=0))
    tc_media = tc.groupby("cajero").mean()
    tc_media.loc["Total"] = tc_media.sum()
    tc_media["Total"] = tc_media.sum(axis=1)
    tc_media.round(2).to_csv(DATA / "usuarios_tipo_cajero.csv")
    tr = act.groupby(["replica", "tipo"]).size().unstack(fill_value=0).reindex(columns=pq.TIPOS, fill_value=0)
    tr["Total"] = tr.sum(axis=1)
    tr.to_csv(DATA / "usuarios_tipo_replica.csv")
    pt = act.groupby("tipo")[["espera", "uso", "sistema"]].mean().reindex(pq.TIPOS)
    pt.round(4).to_csv(DATA / "por_tipo.csv")

    # Punto 3: criterio de decisión por escenario
    dec = []
    for e, g in est.groupby("escenario", sort=False):
        por_rep = g.groupby("replica").agg(espera=("espera", "mean"),
                                           p10=("espera", lambda x: (x > 10).mean()))
        m, _, lo, hi = ic95(por_rep["espera"])
        n_caj, unica = pq.ESCENARIOS[e]
        p10 = por_rep["p10"].mean()
        dec.append({"escenario": e, "descripcion": pq.DESCRIPCION[e], "cajeros": n_caj, "fila_unica": unica,
                    "espera": m, "ic_inf": lo, "ic_sup": hi, "p_espera_10": p10,
                    "espera_p95": g["espera"].quantile(0.95), "espera_max": g["espera"].max(),
                    "utilizacion": caj[caj.escenario == e]["utilizacion"].mean(),
                    "cumple": bool(m <= META_ESPERA and p10 <= META_P10)})
    dec = pd.DataFrame(dec)
    dec.round(4).to_csv(DATA / "decision.csv", index=False)
    piv = est.groupby(["escenario", "replica"])["espera"].mean().unstack(0)
    comp = []
    for a, b in [("S0_3_filas", "S1_4_filas"), ("S0_3_filas", "S3_3_fila_unica"),
                 ("S1_4_filas", "S3_3_fila_unica"), ("S3_3_fila_unica", "S2_5_filas")]:
        m, _, lo, hi = ic95(piv[a] - piv[b])
        comp.append({"a": a, "b": b, "dif": m, "ic_inf": lo, "ic_sup": hi,
                     "p": stats.ttest_rel(piv[a], piv[b]).pvalue})
    comp = pd.DataFrame(comp)
    comp.round(6).to_csv(DATA / "comparaciones.csv", index=False)

    # Sensibilidad al reparto lento / muy lento (supuesto del modelo)
    sens = []
    for nombre, pl, pml in [("15 % lento / 40 % muy lento", 0.15, 0.40),
                            ("27,5 % / 27,5 % (base)", 0.275, 0.275),
                            ("40 % lento / 15 % muy lento", 0.40, 0.15)]:
        probs = {"Rápido": 0.25, "Normal": 0.20, "Lento": pl, "Muy lento": pml}
        for e in ["S0_3_filas", "S1_4_filas", "S3_3_fila_unica"]:
            w = [a_tabla(pq.simular(e, s, probs=probs)).query("llegada >= @t_warm")["espera"].mean()
                 for s in range(1, N + 1)]
            sens.append({"reparto": nombre, "escenario": e, "espera": float(np.mean(w))})
    sens = pd.DataFrame(sens)
    sens.round(4).to_csv(DATA / "sensibilidad.csv", index=False)

    # ---------------------------------------------------------------- 3. calibración y validación
    teo = pq.valores_teoricos()
    gen = [pq.generar_usuarios(s) for s in range(20_001, 20_501)]
    usos = pd.DataFrame([(t, u) for g in gen for _, t, u in g], columns=["tipo", "uso"])
    calib = usos.groupby("tipo")["uso"].agg(media_simulada="mean", n="count").reindex(pq.TIPOS)
    calib["media_tabla"] = [pq.TABLA[t][0] for t in pq.TIPOS]
    calib["proporcion_simulada"] = calib["n"] / calib["n"].sum()
    calib["proporcion_supuesta"] = [pq.TABLA[t][2] for t in pq.TIPOS]
    calib.round(4).to_csv(DATA / "calibracion.csv")
    usos.sample(20_000, random_state=1).round(4).to_csv(DATA / "muestra_usos.csv", index=False)
    a0d = dec.set_index("escenario").loc["S0_3_filas"]
    val = [
        ("Usuarios por día, teórico", teo["usuarios_dia"]),
        ("Usuarios por día, simulado (500 jornadas)", float(np.mean([len(g) for g in gen]))),
        ("Uso medio del cajero, teórico (min)", teo["media_uso"]),
        ("Uso medio del cajero, simulado (min)", float(usos["uso"].mean())),
        ("ρ por cajero, teórico", teo["rho"]),
        ("Utilización por cajero, simulada", float(a0d["utilizacion"])),
        ("Wq aproximación de Kingman G/G/1 (min)", teo["wq_kingman"]),
        ("Wq fórmula de Pollaczek-Khinchine M/G/1 (min)", teo["wq_pk"]),
        ("Wq simulada, estado estable (min)", float(a0d["espera"])),
        ("Lq simulada por cajero (personas)", float(a0["lq"].mean())),
        ("Lq por ley de Little, λ·Wq (personas)", teo["lambda_cajero"] * float(a0d["espera"])),
    ]
    val = pd.DataFrame(val, columns=["indicador", "valor"])
    val.round(4).to_csv(DATA / "validacion.csv", index=False)

    with pd.ExcelWriter(DATA / "resultados_simulacion_parqueadero.xlsx") as xl:
        pd.Series(params).to_frame("valor").to_excel(xl, sheet_name="estado_estable")
        welch.round(4).to_excel(xl, sheet_name="welch", index=False)
        acum.round(4).to_excel(xl, sheet_name="media_acumulada", index=False)
        pd.read_csv(DATA / "antes_despues.csv").to_excel(xl, sheet_name="antes_despues", index=False)
        res_caj.round(4).to_excel(xl, sheet_name="p1_resumen_cajero", index=False)
        caj.round(4).to_excel(xl, sheet_name="p1_cajero_replica", index=False)
        tc_media.round(2).to_excel(xl, sheet_name="p2_usuarios_tipo_cajero")
        tr.to_excel(xl, sheet_name="p2_usuarios_tipo_replica")
        pt.round(4).to_excel(xl, sheet_name="p2_por_tipo")
        dec.round(4).to_excel(xl, sheet_name="p3_decision", index=False)
        comp.round(6).to_excel(xl, sheet_name="p3_comparaciones", index=False)
        sens.round(4).to_excel(xl, sheet_name="p3_sensibilidad", index=False)
        calib.round(4).to_excel(xl, sheet_name="p4_calibracion")
        val.round(4).to_excel(xl, sheet_name="p4_validacion", index=False)
        est.drop(columns="usuario").round(4).to_excel(xl, sheet_name="registros_estables", index=False)

    (DATA / "entorno.txt").write_text(
        f"python {sys.version.split()[0]} ({platform.system()})\nsimpy {simpy.__version__}\n"
        f"numpy {np.__version__}\npandas {pd.__version__}\nscipy {scipy.__version__}\n", encoding="utf8")
    print(pd.Series(params).to_string())
    print(dec[["escenario", "espera", "p_espera_10", "utilizacion", "cumple"]].round(3).to_string(index=False))
    print(res_caj[(res_caj.escenario == "S0_3_filas") & (res_caj.metrica == "t_uso")].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
