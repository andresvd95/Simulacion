"""Verificación cruzada de Forward y Viterbi contra hmmlearn."""
import numpy as np
import pytest

from hmm_churn.algorithms import forward, viterbi
from hmm_churn.model import SCENARIOS
from hmm_churn.simulate import simulate

hmmlearn_hmm = pytest.importorskip("hmmlearn.hmm")


def _reference_model(hmm):
    model = hmmlearn_hmm.CategoricalHMM(n_components=hmm.n_states)
    model.startprob_ = hmm.pi
    model.transmat_ = hmm.A
    model.emissionprob_ = hmm.B
    model.n_features = hmm.n_symbols
    return model


@pytest.mark.parametrize("name", ["base", "mala_red", "retencion"])
def test_loglik_matches_hmmlearn(name):
    hmm = SCENARIOS[name]
    ref = _reference_model(hmm)
    _, obs = simulate(hmm, n_clients=20, n_weeks=52, seed=1)
    for seq in obs:
        _, ours = forward(hmm, seq)
        theirs = ref.score(seq.reshape(-1, 1))
        assert abs(ours - theirs) < 1e-6


@pytest.mark.parametrize("name", ["base", "mala_red", "retencion"])
def test_viterbi_matches_hmmlearn(name):
    hmm = SCENARIOS[name]
    ref = _reference_model(hmm)
    _, obs = simulate(hmm, n_clients=20, n_weeks=52, seed=1)
    for seq in obs:
        path, logp = viterbi(hmm, seq)
        theirs_logp, theirs_path = ref.decode(seq.reshape(-1, 1))
        assert np.array_equal(path, theirs_path)
        assert abs(logp - theirs_logp) < 1e-6
