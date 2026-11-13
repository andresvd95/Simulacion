# Actividad 2: Modelo Oculto de Markov para el abandono de clientes de un ISP

Simulación reproducible de un Modelo Oculto de Markov (HMM) que representa el estado de satisfacción, no observable, de un cliente de Internet residencial a partir de las señales semanales que sí deja la relación con la empresa. Incluye implementación propia de Forward, Viterbi y Baum-Welch, tres escenarios, análisis estadístico y análisis de sensibilidad.

> **Los datos son simulados.** No hay datos reales de clientes: las matrices son supuestos razonados y se declaran como tales en el informe.

## El modelo

| Componente | Definición |
|---|---|
| Estados ocultos S | **F** Fidelizado, **R** En riesgo, **A** Abandono inminente |
| Observaciones V (semanales) | **N** Sin novedad, **T** Reclamo técnico, **P** Pago tardío, **C** Contacto de retención o baja |
| π | [0.80, 0.15, 0.05] |
| A (transición) | F → [0.92, 0.07, 0.01]; R → [0.20, 0.65, 0.15]; A → [0.05, 0.25, 0.70] |
| B (emisión, columnas N, T, P, C) | F → [0.85, 0.08, 0.06, 0.01]; R → [0.45, 0.30, 0.20, 0.05]; A → [0.15, 0.25, 0.30, 0.30] |

Escenarios: `base`, `mala_red` (más transiciones hacia el riesgo y más reclamos técnicos) y `retencion` (campaña que devuelve clientes a Fidelizado). Sus matrices están en `src/hmm_churn/model.py`.

## Requisitos

- Python 3.12 (probado con 3.12.14).
- Dependencias con versión fijada en `requirements.txt`: numpy, scipy, pandas, matplotlib, pillow, pytest y hmmlearn (este último solo para verificar Forward y Viterbi).

## Cómo reproducir

Desde esta carpeta (`Actividad 2/`), con [uv](https://docs.astral.sh/uv/):

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt   # Windows
# Linux/macOS: uv pip install --python .venv/bin/python -r requirements.txt

python run_experiments.py   # 30 semillas por escenario; escribe los CSV en data/
python make_figures.py      # lee data/ y escribe las figuras PNG (300 dpi) en figures/
python -m pytest            # pruebas
```

(Use el `python` del entorno virtual: `.venv\Scripts\python` en Windows o `.venv/bin/python` en Linux/macOS.)

`python run_experiments.py --quick` ejecuta una versión corta (3 semillas) para comprobar que todo funciona. La corrida completa tarda varios minutos.

## Reproducibilidad

- Cada simulación usa `numpy.random.default_rng(semilla)`. Las semillas van de 1 a 30 y cada escenario usa un rango distinto (`semilla + 1000 × índice del escenario`), de modo que las muestras de cada escenario son independientes.
- La inicialización de Baum-Welch también es determinista (semilla derivada de la del experimento).
- `tests/test_reproducibility.py` ejecuta el experimento dos veces en procesos distintos y exige que los CSV sean idénticos byte a byte.
- `data/entorno.txt` guarda las versiones de Python y de las librerías con las que se generaron los resultados.

## Contenido

```text
Actividad 2/
├── README.md
├── requirements.txt
├── pytest.ini
├── run_experiments.py        # Experimentos -> data/*.csv
├── make_figures.py           # Figuras -> figures/*.png
├── src/hmm_churn/
│   ├── model.py              # HMM (π, A, B) y escenarios
│   ├── simulate.py           # Simulación de clientes
│   ├── algorithms.py         # Forward, Viterbi, Baum-Welch (log-espacio)
│   └── metrics.py            # Precisión, recall, alineación de estados, IC 95 %, Welch, d de Cohen
├── tests/                    # Pruebas (verificación contra enumeración exhaustiva y contra hmmlearn)
├── data/                     # Resultados crudos y resúmenes (CSV)
├── figures/                  # Figuras a 300 dpi
├── informe/                  # Informe y referencias verificadas
└── video/                    # Video de sustentación (MP4)
```

## Archivos de resultados

| Archivo | Contenido |
|---|---|
| `data/resultados_crudos.csv` | Una fila por escenario y semilla con todas las métricas |
| `data/resumen_escenarios.csv` | Media, desviación estándar, mínimo, máximo e IC 95 % por escenario y métrica |
| `data/comparacion_escenarios.csv` | Prueba t de Welch y d de Cohen entre pares de escenarios |
| `data/sensibilidad.csv` | Longitud de la secuencia, perturbación de A y de π |
| `data/entorno.txt` | Versiones del entorno |

## Resultados principales

30 semillas por escenario, 200 clientes y 52 semanas por simulación. La línea base es la precisión de un clasificador que siempre predice el estado más frecuente. Detalle completo (media, desviación estándar, mínimo, máximo e IC 95 %) en `data/resumen_escenarios.csv`.

| Escenario | Precisión de Viterbi (media, IC 95 %) | Línea base | Recall del estado R | Error de A tras Baum-Welch |
|---|---|---|---|---|
| base | 0.769 [0.766, 0.772] | 0.658 | 0.299 | 0.203 |
| mala_red | 0.672 [0.669, 0.675] | 0.372 | 0.483 | 0.171 |
| retencion | 0.856 [0.853, 0.859] | 0.836 | 0.145 | 0.330 |

Lectura honesta: Viterbi recupera bien el estado Fidelizado y mal el estado En riesgo; en el escenario de retención casi no supera al clasificador trivial; Baum-Welch converge en las 90 corridas, pero la verosimilitud es casi plana y los parámetros se recuperan de forma solo moderada. El análisis completo está en `informe/informe.pdf`.

## Informe y video

- `informe/informe.docx` y `informe/informe.pdf`: documento con estructura de artículo, con las referencias en formato IEEE (verificadas contra Crossref). Todas las cifras del informe salen de los CSV de `data/`.
- **Video de sustentación** (2:59, 1080p): [`video/sustentacion_actividad2.mp4`](video/sustentacion_actividad2.mp4) en este repositorio, o en línea en [Google Drive](https://drive.google.com/file/d/1gEQABhi_-b80S9EkxEyYn1jE1u-FmHNd/view?usp=sharing).

## Declaración de uso de inteligencia artificial

Se utilizó una herramienta de inteligencia artificial generativa de forma moderada, como apoyo en la programación, la redacción y la revisión de este trabajo. El autor definió el problema y el alcance, revisó y verificó los resultados y las referencias, y es responsable del contenido y de las conclusiones.

## Verificación

Las pruebas comparan Forward y Viterbi con la enumeración exhaustiva de trayectorias en secuencias cortas y con `hmmlearn` en los tres escenarios; comprueban que no hay desbordamiento numérico con 5000 semanas, que la log-verosimilitud de Baum-Welch no decrece y que el código tolera secuencias de longitud 1, probabilidades cero y símbolos ausentes en el entrenamiento.
