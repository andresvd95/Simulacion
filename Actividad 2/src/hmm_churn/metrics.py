"""Métricas de desempeño y estadística descriptiva/inferencial."""
from __future__ import annotations

import itertools
from typing import Sequence

import numpy as np
from scipy import stats

from hmm_churn.model import HMM


def viterbi_accuracy(true: np.ndarray, pred: np.ndarray) -> float:
    """Fracción de estados ocultos recuperados correctamente."""
    return float(np.mean(np.asarray(true) == np.asarray(pred)))


def best_permutation_accuracy(true: np.ndarray, pred: np.ndarray, n_states: int = 3) -> float:
    """Precisión tras elegir la mejor correspondencia entre etiquetas estimadas y verdaderas.

    Un modelo ajustado con Baum-Welch puede nombrar los estados en otro orden;
    como en la simulación se conocen los estados verdaderos, se prueba cada
    permutación de etiquetas y se conserva la de mayor precisión.
    """
    true = np.asarray(true)
    pred = np.asarray(pred)
    best = 0.0
    for perm in itertools.permutations(range(n_states)):
        mapped = np.asarray(perm)[pred]
        best = max(best, float(np.mean(mapped == true)))
    return best


def per_state_recall(true: np.ndarray, pred: np.ndarray, n_states: int = 3) -> np.ndarray:
    """Recall por estado verdadero (NaN si el estado no aparece)."""
    true = np.asarray(true).ravel()
    pred = np.asarray(pred).ravel()
    out = np.full(n_states, np.nan)
    for s in range(n_states):
        mask = true == s
        if mask.any():
            out[s] = np.mean(pred[mask] == s)
    return out


def _permute(model: HMM, perm: Sequence[int]) -> HMM:
    perm = list(perm)
    return HMM(
        pi=model.pi[perm], A=model.A[np.ix_(perm, perm)], B=model.B[perm]
    )


def _distance(reference: HMM, other: HMM) -> float:
    return float(
        np.linalg.norm(reference.A - other.A)
        + np.linalg.norm(reference.B - other.B)
        + np.linalg.norm(reference.pi - other.pi)
    )


def align_permutation(reference: HMM, estimated: HMM) -> HMM:
    """Reordena los estados del estimado para que coincidan con la referencia.

    Baum-Welch puede devolver los estados en otro orden; se prueban todas las
    permutaciones y se elige la de menor distancia.
    """
    best, best_d = estimated, np.inf
    for perm in itertools.permutations(range(estimated.n_states)):
        candidate = _permute(estimated, perm)
        d = _distance(reference, candidate)
        if d < best_d:
            best, best_d = candidate, d
    return best


def param_error(reference: HMM, estimated: HMM) -> dict[str, float]:
    """Norma de Frobenius (A, B) y L2 (pi) entre referencia y estimado alineado."""
    aligned = align_permutation(reference, estimated)
    return {
        "A": float(np.linalg.norm(reference.A - aligned.A)),
        "B": float(np.linalg.norm(reference.B - aligned.B)),
        "pi": float(np.linalg.norm(reference.pi - aligned.pi)),
    }


def summarize(values: Sequence[float]) -> dict[str, float]:
    """Media, desviación estándar muestral, mínimo, máximo e IC 95 % (t de Student)."""
    x = np.asarray(values, dtype=float)
    n = x.size
    mean = float(x.mean())
    std = float(x.std(ddof=1)) if n > 1 else 0.0
    if n > 1 and std > 0:
        low, high = stats.t.interval(0.95, n - 1, loc=mean, scale=std / np.sqrt(n))
    else:
        low, high = mean, mean
    return {
        "mean": mean,
        "std": std,
        "min": float(x.min()),
        "max": float(x.max()),
        "ci_low": float(low),
        "ci_high": float(high),
    }


def compare(a: Sequence[float], b: Sequence[float]) -> dict[str, float]:
    """Prueba t de Welch y d de Cohen entre dos muestras."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    na, nb = a.size, b.size
    pooled = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    if pooled == 0:
        # Muestras constantes: la prueba de Welch y d de Cohen no están definidas.
        return {"welch_t": float("nan"), "p_value": float("nan"), "cohen_d": float("nan")}
    t, p = stats.ttest_ind(a, b, equal_var=False)
    d = float((a.mean() - b.mean()) / pooled)
    return {"welch_t": float(t), "p_value": float(p), "cohen_d": d}
