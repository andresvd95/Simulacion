import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FIGURES = [
    "fig1_trayectorias.png",
    "fig2_precision_escenarios.png",
    "fig3_sensibilidad.png",
    "fig4_matrices_A.png",
    "fig5_flujo_metodologico.png",
]


def test_figures_exist_and_are_300_dpi(tmp_path):
    data, figs = tmp_path / "data", tmp_path / "figs"
    subprocess.run(
        [sys.executable, str(ROOT / "run_experiments.py"), "--quick", "--out", str(data)],
        check=True, cwd=ROOT,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "make_figures.py"), "--data", str(data), "--out", str(figs)],
        check=True, cwd=ROOT,
    )
    for name in FIGURES:
        path = figs / name
        assert path.exists(), name
        with Image.open(path) as img:
            dpi_x, dpi_y = img.info["dpi"]
            assert abs(dpi_x - 300) < 1 and abs(dpi_y - 300) < 1, name
            assert img.width >= 1500, name
