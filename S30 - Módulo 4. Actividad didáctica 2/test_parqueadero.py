"""Pruebas de verificación del modelo de cajeros. Ejecutar con:  python -m pytest -q"""
import numpy as np
import pytest

import parqueadero as pq
from run_experiments import detectar_transitorio, media_movil, n_media_acumulada


@pytest.mark.parametrize("esc", list(pq.ESCENARIOS))
def test_todos_los_usuarios_se_atienden_una_vez(esc):
    regs = pq.simular(esc, semilla=3)
    assert len(regs) == len(pq.generar_usuarios(3))
    assert len({r.usuario for r in regs}) == len(regs)


@pytest.mark.parametrize("esc", list(pq.ESCENARIOS))
def test_un_cajero_no_atiende_dos_usuarios_a_la_vez(esc):
    regs = pq.simular(esc, semilla=7)
    n_caj = pq.ESCENARIOS[esc][0]
    assert {r.cajero for r in regs} <= set(range(1, n_caj + 1))
    for c in range(1, n_caj + 1):
        tramos = sorted((r.inicio, r.fin) for r in regs if r.cajero == c)
        assert all(a[1] <= b[0] + 1e-9 for a, b in zip(tramos, tramos[1:]))


def test_fifo_y_tiempos_coherentes_en_filas_independientes():
    regs = pq.simular("S0_3_filas", semilla=11)
    for r in regs:
        assert r.inicio >= r.llegada - 1e-9 and r.fin > r.inicio
    for c in (1, 2, 3):
        fila = sorted((r for r in regs if r.cajero == c), key=lambda r: r.llegada)
        assert all(a.inicio <= b.inicio + 1e-9 for a, b in zip(fila, fila[1:]))  # sin colarse ni cambiar de fila


def test_fila_unica_no_deja_cajeros_ociosos_con_gente_esperando():
    regs = pq.simular("S3_3_fila_unica", semilla=4)
    for r in regs:
        if r.inicio > r.llegada + 1e-6:  # esperó: justo antes de empezar, los 3 cajeros estaban ocupados
            ocupados = sum(1 for o in regs if o.inicio <= r.inicio - 1e-6 < o.fin)
            assert ocupados == 3


def test_reproducible_y_numeros_aleatorios_comunes():
    a = pq.simular("S0_3_filas", semilla=2)
    b = pq.simular("S0_3_filas", semilla=2)
    assert [(r.usuario, r.cajero, r.fin) for r in a] == [(r.usuario, r.cajero, r.fin) for r in b]
    u1 = {r.usuario: r.fin - r.inicio for r in a}
    u2 = {r.usuario: r.fin - r.inicio for r in pq.simular("S4_4_fila_unica", semilla=2)}
    assert u1.keys() == u2.keys() and all(abs(u1[k] - u2[k]) < 1e-9 for k in u1)


def test_entradas_coinciden_con_la_tabla():
    teo = pq.valores_teoricos()
    gen = [pq.generar_usuarios(s) for s in range(500, 800)]
    assert abs(np.mean([len(g) for g in gen]) - teo["usuarios_dia"]) < 4
    usos = [u for g in gen for _, _, u in g]
    assert abs(np.mean(usos) - teo["media_uso"]) < 0.06
    for tipo in pq.TIPOS:
        v = [u for g in gen for _, t, u in g if t == tipo]
        assert abs(np.mean(v) / pq.TABLA[tipo][0] - 1) < 0.03


def test_mas_cajeros_reduce_la_espera():
    def espera(esc):
        regs = [r for s in range(1, 21) for r in pq.simular(esc, s)]
        return np.mean([r.inicio - r.llegada for r in regs])
    assert espera("S0_3_filas") > espera("S1_4_filas") > espera("S4_4_fila_unica")


def test_algoritmo_de_transitorio_y_replicas():
    t = np.arange(60) * 10.0
    y = 10 * (1 - np.exp(-t / 80))           # curva sintética: sube y se estabiliza en 10
    mm = media_movil(y, 3)
    fin, nivel = detectar_transitorio(t, mm, tol=0.10)
    assert 150 <= fin <= 230 and abs(nivel - 10) < 0.2
    serie = np.array([5, 15, 12, 10.6, 10.2, 10.1, 10.0, 10.0])
    assert n_media_acumulada(serie, tol=0.05) == 5  # 10,6 (n = 4) aún sale de ±5 % de 10
