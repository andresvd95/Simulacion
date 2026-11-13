"""Simulación de trayectorias de clientes a partir de un HMM."""
from __future__ import annotations

import numpy as np

from hmm_churn.model import HMM


def _sample_categorical(cum: np.ndarray, u: np.ndarray) -> np.ndarray:
    """Muestrea índices dadas probabilidades acumuladas (..., K) y uniformes u (...)."""
    idx = (u[..., None] >= cum).sum(axis=-1)
    return np.minimum(idx, cum.shape[-1] - 1)


def simulate(
    hmm: HMM, n_clients: int, n_weeks: int, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    """Simula `n_clients` trayectorias de `n_weeks` semanas.

    Devuelve (estados, observaciones), ambos enteros de forma (n_clients, n_weeks).
    El generador es `np.random.default_rng(seed)`: misma semilla, mismo resultado.
    """
    rng = np.random.default_rng(seed)
    cum_pi = np.cumsum(hmm.pi)
    cum_A = np.cumsum(hmm.A, axis=1)
    cum_B = np.cumsum(hmm.B, axis=1)

    u_state = rng.random((n_clients, n_weeks))
    u_obs = rng.random((n_clients, n_weeks))

    states = np.empty((n_clients, n_weeks), dtype=np.int64)
    states[:, 0] = _sample_categorical(cum_pi, u_state[:, 0])
    for t in range(1, n_weeks):
        states[:, t] = _sample_categorical(cum_A[states[:, t - 1]], u_state[:, t])
    obs = _sample_categorical(cum_B[states], u_obs)
    return states, obs
