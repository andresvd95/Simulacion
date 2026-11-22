"""Pruebas del modelo de cajas. Ejecutar con:  python -m pytest -q"""
import numpy as np
import pytest

import banco


@pytest.mark.parametrize("esc", list(banco.ESCENARIOS))
def test_todos_los_usuarios_se_atienden_una_vez(esc):
    regs = banco.simular(esc, semilla=3)
    assert len(regs) == len(banco.generar_usuarios(3))
    assert len({r.usuario for r in regs}) == len(regs)


@pytest.mark.parametrize("esc", list(banco.ESCENARIOS))
def test_cada_usuario_va_a_una_caja_habilitada(esc):
    for r in banco.simular(esc, semilla=5):
        assert r.operacion in banco.ESCENARIOS[esc][r.caja - 1]
        assert r.inicio >= r.llegada - 1e-9 and r.fin > r.inicio


def test_una_caja_no_atiende_dos_usuarios_a_la_vez():
    regs = banco.simular("E0_3mixtas", semilla=7)
    for c in (1, 2, 3):
        tramos = sorted((r.inicio, r.fin) for r in regs if r.caja == c)
        assert all(a[1] <= b[0] + 1e-9 for a, b in zip(tramos, tramos[1:]))


def test_reproducible_y_numeros_comunes():
    a = banco.simular("E1_1R_2P", semilla=2)
    b = banco.simular("E1_1R_2P", semilla=2)
    assert [(r.usuario, r.caja, r.fin) for r in a] == [(r.usuario, r.caja, r.fin) for r in b]
    s1 = {r.usuario: r.servicio for r in a}
    s2 = {r.usuario: r.servicio for r in banco.simular("E2_2R_1P", semilla=2)}
    assert s1.keys() == s2.keys() and all(abs(s1[k] - s2[k]) < 1e-9 for k in s1)


def test_llegadas_coinciden_con_la_teoria():
    n = [len(banco.generar_usuarios(s)) for s in range(500, 900)]
    assert abs(np.mean(n) - banco.valores_teoricos()["usuarios_dia"]) < 4
