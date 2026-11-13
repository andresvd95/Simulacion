"""Definición del HMM de churn y de los tres escenarios de simulación.

Estados ocultos (S): F = Fidelizado, R = En riesgo, A = Abandono inminente.
Observaciones semanales (V): N = Sin novedad, T = Reclamo técnico,
P = Pago tardío, C = Contacto de retención o baja.

Todos los valores son supuestos razonados, no están calibrados con datos reales.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

STATES = ("F", "R", "A")
SYMBOLS = ("N", "T", "P", "C")

_TOL = 1e-9


def _check_stochastic(name: str, matrix: np.ndarray) -> None:
    if np.any(matrix < 0):
        raise ValueError(f"{name} contiene probabilidades negativas")
    sums = matrix.sum(axis=-1)
    if not np.allclose(sums, 1.0, atol=_TOL):
        raise ValueError(f"las filas de {name} deben sumar 1, suman {sums}")


@dataclass(frozen=True)
class HMM:
    """Modelo lambda = (pi, A, B).

    pi: distribución inicial, forma (N,).
    A:  matriz de transición, A[i, j] = P(S_{t+1}=j | S_t=i), forma (N, N).
    B:  matriz de emisión, B[i, k] = P(O_t=k | S_t=i), forma (N, M).
    """

    pi: np.ndarray
    A: np.ndarray
    B: np.ndarray

    def __post_init__(self) -> None:
        pi = np.asarray(self.pi, dtype=float)
        A = np.asarray(self.A, dtype=float)
        B = np.asarray(self.B, dtype=float)
        object.__setattr__(self, "pi", pi)
        object.__setattr__(self, "A", A)
        object.__setattr__(self, "B", B)
        self.validate()

    @property
    def n_states(self) -> int:
        return self.A.shape[0]

    @property
    def n_symbols(self) -> int:
        return self.B.shape[1]

    def validate(self) -> None:
        n = self.pi.shape[0]
        if self.A.shape != (n, n):
            raise ValueError("A debe ser cuadrada y compatible con pi")
        if self.B.ndim != 2 or self.B.shape[0] != n:
            raise ValueError("B debe tener una fila por estado")
        _check_stochastic("pi", self.pi)
        _check_stochastic("A", self.A)
        _check_stochastic("B", self.B)


_PI = [0.80, 0.15, 0.05]

_A_BASE = [
    [0.92, 0.07, 0.01],
    [0.20, 0.65, 0.15],
    [0.05, 0.25, 0.70],
]
_B_BASE = [
    [0.85, 0.08, 0.06, 0.01],
    [0.45, 0.30, 0.20, 0.05],
    [0.15, 0.25, 0.30, 0.30],
]

_A_RED = [
    [0.84, 0.15, 0.01],
    [0.12, 0.68, 0.20],
    [0.03, 0.22, 0.75],
]
_B_RED = [
    [0.80, 0.13, 0.06, 0.01],
    [0.38, 0.40, 0.17, 0.05],
    [0.12, 0.33, 0.27, 0.28],
]

_A_RETENCION = [
    [0.95, 0.045, 0.005],
    [0.30, 0.60, 0.10],
    [0.12, 0.33, 0.55],
]

SCENARIOS: dict[str, HMM] = {
    "base": HMM(pi=_PI, A=_A_BASE, B=_B_BASE),
    "mala_red": HMM(pi=_PI, A=_A_RED, B=_B_RED),
    "retencion": HMM(pi=_PI, A=_A_RETENCION, B=_B_BASE),
}
