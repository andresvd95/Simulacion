import numpy as np
from scipy import stats

from hmm_churn.metrics import (
    align_permutation,
    best_permutation_accuracy,
    compare,
    param_error,
    per_state_recall,
    summarize,
    viterbi_accuracy,
)
from hmm_churn.model import HMM, SCENARIOS


def test_summarize_known_values():
    out = summarize([1, 2, 3, 4, 5])
    assert out["mean"] == 3.0
    assert np.isclose(out["std"], np.sqrt(2.5))
    assert out["min"] == 1 and out["max"] == 5
    low, high = stats.t.interval(0.95, 4, loc=3, scale=np.sqrt(2.5) / np.sqrt(5))
    assert np.isclose(out["ci_low"], low) and np.isclose(out["ci_high"], high)


def test_viterbi_accuracy():
    true = np.array([[0, 1, 2, 0]])
    assert viterbi_accuracy(true, true) == 1.0
    pred = np.array([[0, 1, 0, 1]])
    assert viterbi_accuracy(true, pred) == 0.5


def test_recall_perfect_and_zero():
    true = np.array([0, 1, 2, 0, 1, 2])
    assert np.allclose(per_state_recall(true, true), [1, 1, 1])
    assert np.allclose(per_state_recall(true, (true + 1) % 3), [0, 0, 0])


def test_align_permutation_recovers_relabeled_model():
    base = SCENARIOS["base"]
    perm = [2, 0, 1]
    relabeled = HMM(
        pi=base.pi[perm], A=base.A[np.ix_(perm, perm)], B=base.B[perm]
    )
    aligned = align_permutation(base, relabeled)
    assert np.allclose(aligned.A, base.A)
    assert np.allclose(aligned.B, base.B)
    assert np.allclose(aligned.pi, base.pi)
    err = param_error(base, relabeled)
    assert err["A"] < 1e-9 and err["B"] < 1e-9 and err["pi"] < 1e-9


def test_param_error_positive_for_different_models():
    err = param_error(SCENARIOS["base"], SCENARIOS["mala_red"])
    assert err["A"] > 0 and err["B"] > 0


def test_compare_identical_samples_d_zero():
    a = [1.0, 2.0, 3.0, 4.0]
    out = compare(a, list(a))
    assert out["cohen_d"] == 0.0
    assert np.isclose(out["p_value"], 1.0)
    assert out["welch_t"] == 0.0


def test_compare_constant_samples_returns_nan_without_warnings():
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        out = compare([1.0, 1.0, 1.0], [1.0, 1.0, 1.0])
    assert np.isnan(out["welch_t"]) and np.isnan(out["p_value"]) and np.isnan(out["cohen_d"])


def test_best_permutation_accuracy_ignores_label_order():
    true = np.array([[0, 1, 2, 0, 1, 2]])
    relabeled = (true + 1) % 3
    assert viterbi_accuracy(true, relabeled) == 0.0
    assert best_permutation_accuracy(true, relabeled) == 1.0
    assert best_permutation_accuracy(true, true) == 1.0
