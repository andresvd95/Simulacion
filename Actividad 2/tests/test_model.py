import numpy as np
import pytest

from hmm_churn.model import HMM, SCENARIOS, STATES, SYMBOLS


def test_scenarios_rows_sum_to_one():
    assert set(SCENARIOS) == {"base", "mala_red", "retencion"}
    for hmm in SCENARIOS.values():
        assert np.isclose(hmm.pi.sum(), 1.0)
        assert np.allclose(hmm.A.sum(axis=1), 1.0)
        assert np.allclose(hmm.B.sum(axis=1), 1.0)


def test_dimensions_and_labels():
    assert STATES == ("F", "R", "A")
    assert SYMBOLS == ("N", "T", "P", "C")
    base = SCENARIOS["base"]
    assert base.pi.shape == (3,)
    assert base.A.shape == (3, 3)
    assert base.B.shape == (3, 4)


def test_base_values_match_spec():
    base = SCENARIOS["base"]
    assert np.allclose(base.pi, [0.80, 0.15, 0.05])
    assert np.allclose(base.A[0], [0.92, 0.07, 0.01])
    assert np.allclose(base.A[1], [0.20, 0.65, 0.15])
    assert np.allclose(base.A[2], [0.05, 0.25, 0.70])
    assert np.allclose(base.B[0], [0.85, 0.08, 0.06, 0.01])
    assert np.allclose(base.B[1], [0.45, 0.30, 0.20, 0.05])
    assert np.allclose(base.B[2], [0.15, 0.25, 0.30, 0.30])


def test_other_scenarios_match_spec():
    red = SCENARIOS["mala_red"]
    assert np.allclose(red.A[0], [0.84, 0.15, 0.01])
    assert np.allclose(red.B[1], [0.38, 0.40, 0.17, 0.05])
    ret = SCENARIOS["retencion"]
    assert np.allclose(ret.A[0], [0.95, 0.045, 0.005])
    assert np.allclose(ret.A[2], [0.12, 0.33, 0.55])
    assert np.allclose(ret.B, SCENARIOS["base"].B)


def test_invalid_row_sum_raises():
    base = SCENARIOS["base"]
    bad_A = base.A.copy()
    bad_A[0] = [0.90, 0.0, 0.0]
    with pytest.raises(ValueError):
        HMM(pi=base.pi, A=bad_A, B=base.B)


def test_negative_probability_raises():
    base = SCENARIOS["base"]
    bad_B = base.B.copy()
    bad_B[0] = [1.1, -0.1, 0.0, 0.0]
    with pytest.raises(ValueError):
        HMM(pi=base.pi, A=base.A, B=bad_B)
