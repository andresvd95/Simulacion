"""Forward, Viterbi y Baum-Welch en log-espacio (estables para T largo)."""
from __future__ import annotations

import numpy as np
from scipy.special import logsumexp

from hmm_churn.model import HMM


def _log(x: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore"):
        return np.log(x)


def _forward_batch(log_pi, log_A, log_B, obs):
    """log-alfa para un lote de secuencias. obs: (S, T) -> (S, T, N)."""
    S, T = obs.shape
    N = log_pi.shape[0]
    la = np.empty((S, T, N))
    la[:, 0, :] = log_pi[None, :] + log_B[:, obs[:, 0]].T
    for t in range(1, T):
        trans = logsumexp(la[:, t - 1, :, None] + log_A[None, :, :], axis=1)
        la[:, t, :] = trans + log_B[:, obs[:, t]].T
    return la


def _backward_batch(log_A, log_B, obs):
    """log-beta para un lote de secuencias. obs: (S, T) -> (S, T, N)."""
    S, T = obs.shape
    N = log_A.shape[0]
    lb = np.zeros((S, T, N))
    for t in range(T - 2, -1, -1):
        emit_next = log_B[:, obs[:, t + 1]].T  # (S, N)
        lb[:, t, :] = logsumexp(
            log_A[None, :, :] + (emit_next + lb[:, t + 1, :])[:, None, :], axis=2
        )
    return lb


def forward(hmm: HMM, obs: np.ndarray) -> tuple[np.ndarray, float]:
    """Devuelve log-alfa (T, N) y la log-verosimilitud log P(O | lambda)."""
    obs = np.asarray(obs, dtype=np.int64)
    with np.errstate(invalid="ignore"):
        la = _forward_batch(_log(hmm.pi), _log(hmm.A), _log(hmm.B), obs[None, :])[0]
        loglik = float(logsumexp(la[-1]))
    return la, loglik


def viterbi(hmm: HMM, obs: np.ndarray) -> tuple[np.ndarray, float]:
    """Camino de estados más probable y su log-probabilidad conjunta."""
    obs = np.asarray(obs, dtype=np.int64)
    T, N = len(obs), hmm.n_states
    log_pi, log_A, log_B = _log(hmm.pi), _log(hmm.A), _log(hmm.B)
    delta = np.empty((T, N))
    psi = np.zeros((T, N), dtype=np.int64)
    delta[0] = log_pi + log_B[:, obs[0]]
    for t in range(1, T):
        scores = delta[t - 1][:, None] + log_A
        psi[t] = np.argmax(scores, axis=0)
        delta[t] = scores[psi[t], np.arange(N)] + log_B[:, obs[t]]
    path = np.empty(T, dtype=np.int64)
    path[-1] = int(np.argmax(delta[-1]))
    for t in range(T - 2, -1, -1):
        path[t] = psi[t + 1, path[t + 1]]
    return path, float(delta[-1, path[-1]])


def _group_by_length(sequences: list[np.ndarray]) -> list[np.ndarray]:
    groups: dict[int, list[np.ndarray]] = {}
    for seq in sequences:
        seq = np.asarray(seq, dtype=np.int64)
        groups.setdefault(len(seq), []).append(seq)
    return [np.stack(g) for g in groups.values()]


def baum_welch(
    sequences: list[np.ndarray],
    init: HMM,
    max_iter: int = 200,
    tol: float = 1e-6,
    smoothing: float = 1e-6,
) -> tuple[HMM, list[float], int]:
    """Reestimación de Baum-Welch (EM) sobre varias secuencias.

    Devuelve (modelo, historial de log-verosimilitud total, iteraciones).
    `tol` es relativa: se detiene cuando la mejora de la log-verosimilitud
    entre dos iteraciones es menor que `tol` veces su valor absoluto.
    `smoothing` es un pseudo-conteo que evita probabilidades exactamente cero
    (p. ej. un símbolo que nunca aparece en los datos de entrenamiento).
    """
    groups = _group_by_length(sequences)
    n_seq = sum(g.shape[0] for g in groups)
    N, M = init.n_states, init.n_symbols
    model = init
    history: list[float] = []

    for _ in range(max_iter):
        log_pi, log_A, log_B = _log(model.pi), _log(model.A), _log(model.B)
        total_ll = 0.0
        g0 = np.zeros(N)
        xi_sum = np.zeros((N, N))
        emit_sum = np.zeros((N, M))
        for obs in groups:
            la = _forward_batch(log_pi, log_A, log_B, obs)
            lb = _backward_batch(log_A, log_B, obs)
            ll = logsumexp(la[:, -1, :], axis=1)  # (S,)
            total_ll += float(ll.sum())
            gamma = np.exp(la + lb - ll[:, None, None])  # (S, T, N)
            g0 += gamma[:, 0, :].sum(axis=0)
            if obs.shape[1] > 1:
                log_xi = (
                    la[:, :-1, :, None]
                    + log_A[None, None, :, :]
                    + log_B[:, obs[:, 1:]].transpose(1, 2, 0)[:, :, None, :]
                    + lb[:, 1:, None, :]
                    - ll[:, None, None, None]
                )
                xi_sum += np.exp(log_xi).sum(axis=(0, 1))
            for k in range(M):
                emit_sum[:, k] += (gamma * (obs == k)[:, :, None]).sum(axis=(0, 1))

        history.append(total_ll)
        if len(history) > 1 and abs(history[-1] - history[-2]) < tol * abs(history[-2]):
            break

        pi_new = (g0 + smoothing) / (n_seq + N * smoothing)
        A_new = xi_sum + smoothing
        A_new /= A_new.sum(axis=1, keepdims=True)
        B_new = emit_sum + smoothing
        B_new /= B_new.sum(axis=1, keepdims=True)
        model = HMM(pi=pi_new, A=A_new, B=B_new)

    return model, history, len(history)


def baum_welch_restarts(
    sequences: list[np.ndarray],
    inits: list[HMM],
    max_iter: int = 200,
    tol: float = 1e-5,
    smoothing: float = 1e-6,
) -> tuple[HMM, list[float], int]:
    """Ejecuta Baum-Welch desde varias inicializaciones y conserva la de mayor
    log-verosimilitud final (EM solo garantiza un óptimo local)."""
    best = None
    for init in inits:
        result = baum_welch(sequences, init, max_iter=max_iter, tol=tol, smoothing=smoothing)
        if best is None or result[1][-1] > best[1][-1]:
            best = result
    return best
