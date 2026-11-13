import numpy as np

from hmm_churn.model import SCENARIOS
from hmm_churn.simulate import simulate


def test_same_seed_same_output():
    hmm = SCENARIOS["base"]
    s1, o1 = simulate(hmm, n_clients=20, n_weeks=30, seed=7)
    s2, o2 = simulate(hmm, n_clients=20, n_weeks=30, seed=7)
    assert np.array_equal(s1, s2)
    assert np.array_equal(o1, o2)


def test_different_seed_differs():
    hmm = SCENARIOS["base"]
    _, o1 = simulate(hmm, n_clients=20, n_weeks=30, seed=1)
    _, o2 = simulate(hmm, n_clients=20, n_weeks=30, seed=2)
    assert not np.array_equal(o1, o2)


def test_shapes_and_ranges():
    hmm = SCENARIOS["base"]
    states, obs = simulate(hmm, n_clients=15, n_weeks=12, seed=3)
    assert states.shape == (15, 12)
    assert obs.shape == (15, 12)
    assert states.min() >= 0 and states.max() <= 2
    assert obs.min() >= 0 and obs.max() <= 3


def test_empirical_matches_parameters():
    hmm = SCENARIOS["base"]
    states, obs = simulate(hmm, n_clients=2000, n_weeks=200, seed=11)
    trans = np.zeros((3, 3))
    for i in range(3):
        for j in range(3):
            trans[i, j] = np.sum((states[:, :-1] == i) & (states[:, 1:] == j))
    trans /= trans.sum(axis=1, keepdims=True)
    emis = np.zeros((3, 4))
    for i in range(3):
        for k in range(4):
            emis[i, k] = np.sum((states == i) & (obs == k))
    emis /= emis.sum(axis=1, keepdims=True)
    assert np.allclose(trans, hmm.A, atol=0.01)
    assert np.allclose(emis, hmm.B, atol=0.01)
    first = np.bincount(states[:, 0], minlength=3) / states.shape[0]
    assert np.allclose(first, hmm.pi, atol=0.03)
