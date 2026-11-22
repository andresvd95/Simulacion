"""Simulación de eventos discretos de las cajas del Banco de Colombia (SimPy).

Cada caja es una cola M/M/1 independiente (un servidor, cola FIFO propia). El
usuario que llega elige, entre las cajas habilitadas para su operación, la de
menor número de personas (en cola + en servicio); los empates se rompen al azar.

Proceso de llegadas (una sola puerta de entrada):
  1. Se sortea la operación del siguiente usuario: retiro (70 %) o pago (30 %).
  2. Se sortea su tipo con la Tabla 2 (probabilidades condicionadas a la operación).
  3. El tiempo hasta su llegada es exponencial con la media de llegada de su tipo (Tabla 1).
  4. Su tiempo de servicio es exponencial con la media de uso de su tipo (Tabla 1).

El banco recibe usuarios durante 8 h (480 min); quienes ya están dentro al cierre
son atendidos (puertas cerradas, cajas abiertas hasta vaciar las colas).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import simpy

JORNADA = 480.0  # minutos
P_RETIRO = 0.70

# (operación, tipo): (media de servicio, media de llegada, probabilidad dentro de la operación)
TABLA = {
    ("Retiro", "Rápido"): (1.0, 1.0, 0.23),
    ("Retiro", "Normal"): (2.0, 2.0, 0.40),
    ("Retiro", "Lento"): (3.0, 3.0, 0.17),
    ("Retiro", "Muy lento"): (4.0, 3.0, 0.20),
    ("Pago", "Rápido"): (3.0, 1.0, 0.10),
    ("Pago", "Normal"): (3.0, 2.0, 0.20),
    ("Pago", "Lento"): (5.0, 3.0, 0.30),
    ("Pago", "Muy lento"): (7.0, 4.0, 0.40),
}
TIPOS = list(TABLA)  # orden fijo de los 8 tipos de usuario
OPERACIONES = ("Retiro", "Pago")

# Escenarios: qué operaciones atiende cada caja.
AMBAS = ("Retiro", "Pago")
ESCENARIOS = {
    "E0_3mixtas": [AMBAS, AMBAS, AMBAS],
    "E1_1R_2P": [("Retiro",), ("Pago",), ("Pago",)],
    "E2_2R_1P": [("Retiro",), ("Retiro",), ("Pago",)],
    "E3_4mixtas": [AMBAS, AMBAS, AMBAS, AMBAS],
    "E4_2R_2P": [("Retiro",), ("Retiro",), ("Pago",), ("Pago",)],
}
DESCRIPCION = {
    "E0_3mixtas": "3 cajas mixtas (situación actual)",
    "E1_1R_2P": "1 caja de retiros + 2 de pagos",
    "E2_2R_1P": "2 cajas de retiros + 1 de pagos",
    "E3_4mixtas": "4 cajas mixtas (caja nueva)",
    "E4_2R_2P": "2 cajas de retiros + 2 de pagos (caja nueva)",
}


@dataclass
class Registro:
    replica: int
    escenario: str
    usuario: int
    operacion: str
    tipo: str
    caja: int
    llegada: float
    inicio: float
    fin: float

    @property
    def espera(self) -> float:
        return self.inicio - self.llegada

    @property
    def servicio(self) -> float:
        return self.fin - self.inicio


def generar_usuarios(semilla: int, jornada: float = JORNADA):
    """Lista de (llegada, operación, tipo, servicio). Depende solo de la semilla, no del
    escenario: así todos los escenarios ven exactamente los mismos usuarios (números
    aleatorios comunes), lo que reduce la varianza de las comparaciones."""
    rng = np.random.default_rng(semilla)
    usuarios = []
    t = 0.0
    while True:
        # 1) Operación del próximo usuario: retiro con probabilidad 0,70
        op = "Retiro" if rng.random() < P_RETIRO else "Pago"
        # 2) Tipo de usuario dentro de la operación (Tabla 2)
        tipos_op = [k for k in TIPOS if k[0] == op]
        probs = np.array([TABLA[k][2] for k in tipos_op])
        clave = tipos_op[rng.choice(len(tipos_op), p=probs / probs.sum())]
        media_srv, media_lleg, _ = TABLA[clave]
        # 3) Tiempo hasta su llegada y tiempo de servicio: exponenciales (Tabla 1)
        t += rng.exponential(media_lleg)
        servicio = rng.exponential(media_srv)
        if t > jornada:  # después de 480 min ya no entra nadie
            break
        usuarios.append((t, clave[0], clave[1], servicio))
    return usuarios


def simular(escenario: str, semilla: int, replica: int | None = None) -> list[Registro]:
    cajas_ops = ESCENARIOS[escenario]
    usuarios = generar_usuarios(semilla)
    rng_desempate = np.random.default_rng(semilla + 7_919)
    env = simpy.Environment()
    # Cada caja es un recurso de capacidad 1 con su propia fila FIFO (M/M/1 independiente)
    cajas = [simpy.Resource(env, capacity=1) for _ in cajas_ops]
    registros: list[Registro] = []

    def ocupacion(c: simpy.Resource) -> int:
        return len(c.queue) + c.count

    def cliente(i, llegada, op, tipo, servicio):
        """Proceso de un usuario: llega, elige caja, espera su turno y es atendido."""
        yield env.timeout(llegada - env.now)
        # Elige, entre las cajas que atienden su operación, la de menos personas
        habilitadas = [j for j, ops in enumerate(cajas_ops) if op in ops]
        menor = min(ocupacion(cajas[j]) for j in habilitadas)
        candidatas = [j for j in habilitadas if ocupacion(cajas[j]) == menor]
        j = candidatas[int(rng_desempate.integers(len(candidatas)))]
        with cajas[j].request() as turno:
            yield turno              # espera en la fila hasta que la caja queda libre
            inicio = env.now
            yield env.timeout(servicio)  # ocupa la caja durante su tiempo de servicio
            registros.append(Registro(replica if replica is not None else semilla, escenario, i, op,
                                      tipo, j + 1, llegada, inicio, env.now))

    for i, (llegada, op, tipo, servicio) in enumerate(usuarios, start=1):
        env.process(cliente(i, llegada, op, tipo, servicio))
    env.run()  # corre hasta atender al último usuario (puertas cerradas a los 480 min)
    return registros


def valores_teoricos():
    """Tasas y cargas esperadas que se deducen de las tablas (sirven para validar)."""
    p_tipo = {k: (P_RETIRO if k[0] == "Retiro" else 1 - P_RETIRO) * TABLA[k][2] for k in TIPOS}
    media_lleg = sum(p * TABLA[k][1] for k, p in p_tipo.items())
    lam = 1 / media_lleg
    out = {"p_tipo": p_tipo, "media_entre_llegadas": media_lleg, "lambda": lam,
           "usuarios_dia": lam * JORNADA}
    for op in OPERACIONES:
        ks = [k for k in TIPOS if k[0] == op]
        p_op = sum(p_tipo[k] for k in ks)
        es = sum(p_tipo[k] * TABLA[k][0] for k in ks) / p_op
        es2 = sum(p_tipo[k] * 2 * TABLA[k][0] ** 2 for k in ks) / p_op  # E[S^2] de la mezcla
        out[op] = {"lambda": lam * p_op, "ES": es, "ES2": es2, "carga": lam * p_op * es}
    return out
