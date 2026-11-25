"""Simulación de eventos discretos de los cajeros de pago del parqueadero Supercentro (SimPy).

Cada punto de salida tiene cajeros de autopago independientes, cada uno con su propia fila
FIFO, sin cambio de fila ni deserción (modelo M/M/1 por cajero, según el enunciado).

Demanda: cada uno de los 3 cajeros actuales recibe un flujo de usuarios con las medias de
llegada de la tabla; la demanda total es la suma de los 3 flujos. Para cada usuario:
  1. Se sortea su tipo: rápido 25 %, normal 20 %, lento y muy lento el 55 % restante
     (supuesto: 27,5 % cada uno, porque el enunciado no los separa).
  2. El tiempo hasta su llegada es exponencial con la media de llegada de su tipo.
  3. Su tiempo de uso del cajero es exponencial con la media de uso de su tipo.

La demanda NO depende del escenario: los mismos usuarios (números aleatorios comunes) se
reparten entre los cajeros de cada configuración, para comparar escenarios de forma justa.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import simpy

HORIZONTE = 720.0   # minutos simulados por réplica (12 h de operación del centro comercial)
FLUJOS = 3          # flujos de demanda: uno por cada cajero actual

# tipo: (media de uso del cajero, media entre llegadas, probabilidad)
TABLA = {
    "Rápido": (1.0, 3.0, 0.25),
    "Normal": (3.0, 3.0, 0.20),
    "Lento": (4.0, 5.0, 0.275),
    "Muy lento": (6.0, 7.0, 0.275),
}
TIPOS = list(TABLA)

# Escenarios: (número de cajeros, ¿fila única compartida?)
ESCENARIOS = {
    "S0_3_filas": (3, False),
    "S1_4_filas": (4, False),
    "S2_5_filas": (5, False),
    "S3_3_fila_unica": (3, True),
    "S4_4_fila_unica": (4, True),
}
DESCRIPCION = {
    "S0_3_filas": "3 cajeros, filas independientes (actual)",
    "S1_4_filas": "4 cajeros, filas independientes",
    "S2_5_filas": "5 cajeros, filas independientes",
    "S3_3_fila_unica": "3 cajeros, fila única",
    "S4_4_fila_unica": "4 cajeros, fila única",
}


@dataclass
class Registro:
    replica: int
    escenario: str
    usuario: int
    tipo: str
    cajero: int
    llegada: float
    inicio: float
    fin: float


def generar_usuarios(semilla: int, horizonte: float = HORIZONTE, probs: dict | None = None):
    """Devuelve la lista ordenada de usuarios (llegada, tipo, uso) de una réplica.

    Se generan FLUJOS flujos independientes; en cada uno, el tipo del siguiente usuario
    define cuánto tarda en llegar (media de llegada) y cuánto usa el cajero (media de uso).
    """
    probs = probs or {t: TABLA[t][2] for t in TIPOS}
    p = np.array([probs[t] for t in TIPOS])
    p = p / p.sum()
    rng = np.random.default_rng(semilla)
    usuarios = []
    for _ in range(FLUJOS):
        t = 0.0
        while True:
            tipo = TIPOS[rng.choice(len(TIPOS), p=p)]
            media_uso, media_lleg, _ = TABLA[tipo]
            t += rng.exponential(media_lleg)       # llegada exponencial según el tipo
            uso = rng.exponential(media_uso)         # tiempo de uso exponencial según el tipo
            if t > horizonte:
                break
            usuarios.append((t, tipo, uso))
    usuarios.sort()
    return usuarios


def simular(escenario: str, semilla: int, replica: int | None = None, probs: dict | None = None) -> list[Registro]:
    """Simula una réplica del escenario y devuelve un registro por usuario atendido."""
    n_cajeros, fila_unica = ESCENARIOS[escenario]
    usuarios = generar_usuarios(semilla, probs=probs)
    rng_asig = np.random.default_rng(semilla + 50_021)  # reparto de usuarios entre filas
    env = simpy.Environment()
    registros: list[Registro] = []
    rep = semilla if replica is None else replica

    if fila_unica:
        # Una sola fila: el primero de la fila pasa al primer cajero que se libere.
        pool = simpy.Store(env, capacity=n_cajeros)
        for k in range(n_cajeros):
            pool.put(k + 1)
    else:
        # Filas independientes: un recurso de capacidad 1 por cajero (M/M/1).
        cajeros = [simpy.Resource(env, capacity=1) for _ in range(n_cajeros)]

    def usuario(i, llegada, tipo, uso):
        yield env.timeout(llegada - env.now)
        if fila_unica:
            k = yield pool.get()                    # espera a que algún cajero quede libre
            inicio = env.now
            yield env.timeout(uso)
            yield pool.put(k)
        else:
            k = int(rng_asig.integers(n_cajeros)) + 1  # elige fila al azar; no cambia ni desiste
            with cajeros[k - 1].request() as turno:
                yield turno
                inicio = env.now
                yield env.timeout(uso)
        registros.append(Registro(rep, escenario, i, tipo, k, llegada, inicio, env.now))

    for i, (llegada, tipo, uso) in enumerate(usuarios, start=1):
        env.process(usuario(i, llegada, tipo, uso))
    env.run()  # se atiende a todos los que llegaron antes del cierre
    return registros


def valores_teoricos(n_cajeros: int = 3):
    """Medias de entrada y aproximación de Kingman (G/G/1) para validar el modelo."""
    p = {t: TABLA[t][2] for t in TIPOS}
    ea = sum(p[t] * TABLA[t][1] for t in TIPOS)                 # media entre llegadas de un flujo
    ea2 = sum(p[t] * 2 * TABLA[t][1] ** 2 for t in TIPOS)
    es = sum(p[t] * TABLA[t][0] for t in TIPOS)                 # media de uso
    es2 = sum(p[t] * 2 * TABLA[t][0] ** 2 for t in TIPOS)
    lam_total = FLUJOS / ea
    lam = lam_total / n_cajeros                                 # llegadas a cada cajero
    rho = lam * es
    ca2 = (ea2 - ea ** 2) / ea ** 2
    cs2 = (es2 - es ** 2) / es ** 2
    # Con reparto aleatorio, la variabilidad de llegadas a un cajero cambia; Kingman es una guía.
    wq_kingman = rho / (1 - rho) * (ca2 + cs2) / 2 * es if rho < 1 else float("inf")
    wq_pk = lam * es2 / (2 * (1 - rho)) if rho < 1 else float("inf")  # Pollaczek-Khinchine
    return {"media_llegada_flujo": ea, "lambda_total": lam_total, "lambda_cajero": lam,
            "media_uso": es, "rho": rho, "ca2": ca2, "cs2": cs2,
            "wq_kingman": wq_kingman, "wq_pk": wq_pk, "usuarios_dia": lam_total * HORIZONTE}
