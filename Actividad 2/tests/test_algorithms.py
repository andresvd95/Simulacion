import itertools

import numpy as np

from hmm_churn.algorithms import baum_welch, baum_welch_restarts, forward, viterbi
from hmm_churn.model import HMM, SCENARIOS
from hmm_churn.simulate import simulate


def _brute_force(hmm: HMM, obs: np.ndarray):
    """Enumera todas las trayectorias de estados (solo para T pequeño)."""
    T = len(obs)
    total = 0.0
    best_p, best_path = -1.0, None
    for path in itertools.product(range(hmm.n_states), repeat=T):
        p = hmm.pi[path[0]] * hmm.B[path[0], obs[0]]
        for t in range(1, T):
            p *= hmm.A[path[t - 1], path[t]] * hmm.B[path[t], obs[t]]
        total += p
        if p > best_p:
            best_p, best_path = p, path
    return np.log(total), np.array(best_path), np.log(best_p)


def test_forward_matches_bruteforce():
    hmm = SCENARIOS["base"]
    obs = np.array([0, 1, 3, 2, 0, 1])
    _, loglik = forward(hmm, obs)
    expected, _, _ = _brute_force(hmm, obs)
    assert np.isclose(loglik, expected)


def test_viterbi_matches_bruteforce():
    hmm = SCENARIOS["base"]
    obs = np.array([0, 1, 3, 2, 0, 1])
    path, logp = viterbi(hmm, obs)
    _, best_path, best_logp = _brute_force(hmm, obs)
    assert np.array_equal(path, best_path)
    assert np.isclose(logp, best_logp)


def test_forward_no_underflow_long_sequence():
    hmm = SCENARIOS["base"]
    _, obs = simulate(hmm, n_clients=1, n_weeks=5000, seed=5)
    _, loglik = forward(hmm, obs[0])
    assert np.isfinite(loglik) and loglik < 0


def test_single_observation():
    hmm = SCENARIOS["base"]
    obs = np.array([2])
    log_alpha, loglik = forward(hmm, obs)
    path, logp = viterbi(hmm, obs)
    expected = np.log(np.sum(hmm.pi * hmm.B[:, 2]))
    assert log_alpha.shape == (1, 3)
    assert np.isclose(loglik, expected)
    assert path.shape == (1,) and np.isfinite(logp)


def test_zero_probabilities_no_nan():
    A = np.array([[0.5, 0.5, 0.0], [0.5, 0.25, 0.25], [0.0, 0.5, 0.5]])
    B = np.array([[1.0, 0.0, 0.0, 0.0], [0.5, 0.5, 0.0, 0.0], [0.0, 0.0, 0.5, 0.5]])
    hmm = HMM(pi=[1.0, 0.0, 0.0], A=A, B=B)
    impossible = np.array([3, 0, 0, 0])  # el estado inicial 0 nunca emite el símbolo 3
    log_alpha, loglik = forward(hmm, impossible)
    path, logp = viterbi(hmm, impossible)
    assert not np.isnan(log_alpha).any()
    assert loglik == -np.inf and logp == -np.inf
    possible = np.array([0, 0, 1, 3])  # camino 0 -> 0 -> 1 -> 2
    _, ok = forward(hmm, possible)
    path_ok, logp_ok = viterbi(hmm, possible)
    assert np.isfinite(ok) and np.isfinite(logp_ok)
    assert list(path_ok) == [0, 0, 1, 2]


def test_baum_welch_loglik_monotone():
    true = SCENARIOS["base"]
    states, obs = simulate(true, n_clients=60, n_weeks=40, seed=21)
    init = HMM(
        pi=[1 / 3] * 3,
        A=[[0.6, 0.3, 0.1], [0.3, 0.4, 0.3], [0.1, 0.3, 0.6]],
        B=[[0.4, 0.2, 0.2, 0.2], [0.3, 0.3, 0.2, 0.2], [0.2, 0.2, 0.3, 0.3]],
    )
    model, history, n_iter = baum_welch(list(obs), init, max_iter=50)
    assert n_iter >= 2 and len(history) == n_iter
    assert np.all(np.diff(history) >= -1e-6)
    assert history[-1] > history[0]
    assert np.allclose(model.A.sum(axis=1), 1.0)
    assert np.allclose(model.B.sum(axis=1), 1.0)


def test_baum_welch_unseen_symbol_no_nan():
    rng = np.random.default_rng(4)
    seqs = [rng.integers(0, 3, size=30) for _ in range(10)]  # nunca aparece el símbolo 3
    model, history, _ = baum_welch(seqs, SCENARIOS["base"], max_iter=20)
    for arr in (model.pi, model.A, model.B):
        assert np.all(np.isfinite(arr))
    assert np.allclose(model.B.sum(axis=1), 1.0)
    assert np.all(np.isfinite(history))


def test_baum_welch_converges_before_max_iter():
    _, obs = simulate(SCENARIOS["base"], n_clients=100, n_weeks=52, seed=3)
    _, history, n_iter = baum_welch(list(obs), SCENARIOS["base"], max_iter=300, tol=1e-5)
    assert n_iter < 300
    relative_gain = abs(history[-1] - history[-2]) / abs(history[-2])
    assert relative_gain < 1e-5


def test_restarts_return_best_loglik():
    _, obs = simulate(SCENARIOS["base"], n_clients=50, n_weeks=40, seed=8)
    rng = np.random.default_rng(0)
    inits = [
        HMM(
            pi=rng.dirichlet(np.ones(3)),
            A=rng.dirichlet(np.ones(3), size=3),
            B=rng.dirichlet(np.ones(4), size=3),
        )
        for _ in range(3)
    ]
    singles = [baum_welch(list(obs), i, max_iter=100, tol=1e-5)[1][-1] for i in inits]
    _, history, _ = baum_welch_restarts(list(obs), inits, max_iter=100, tol=1e-5)
    assert np.isclose(history[-1], max(singles))
