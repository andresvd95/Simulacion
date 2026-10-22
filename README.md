# Simulación de Yahtzee con Montecarlo

Aplicación de consola que simula el Yahtzee clásico para dos jugadores y compara una estrategia basada en Montecarlo con una estrategia greedy. El proyecto corresponde a la Actividad 1 de Simulación.

## Requisitos

- Python 3.11 o superior.
- No requiere instalar paquetes externos.

## Inicio rápido

Desde la carpeta raíz del repositorio, inicia una partida contra el jugador automático:

```bash
python Act1/yahtzee.py play --player1 human --player2 mc
```

También puedes jugar contra otra persona, o ejecutar una comparación automática:

```bash
python Act1/yahtzee.py play --player1 human --player2 human
python Act1/yahtzee.py play --player1 mc --player2 greedy --seed 2026
python Act1/yahtzee.py simulate --games 100 --samples 24 --seed 2026 --output Act1/resultados.json
```

En Windows, si `python` no está en el PATH y tienes [uv](https://docs.astral.sh/uv/) instalado, puedes anteponer `uv run --python 3.12` al comando. Por ejemplo:

```powershell
uv run --python 3.12 Act1/yahtzee.py play --player1 human --player2 mc
```

## Cómo jugar

Cada participante tiene 13 turnos. En cada turno lanza cinco dados de seis caras hasta tres veces y elige una categoría libre para anotar la mano. Para conservar dados, escribe sus posiciones del 1 al 5 separadas por espacios. Pulsa Enter sin escribir posiciones para terminar los lanzamientos y elegir dónde anotar.

La tarjeta contiene seis categorías superiores (unos a seises) y siete inferiores (trío, cuarteto, full, escalera corta, escalera larga, Yahtzee y azar). Se aplican el bono de 35 puntos por alcanzar 63 en la sección superior, los 100 puntos por cada Yahtzee adicional válido y las reglas Joker. Gana quien obtiene el puntaje total más alto tras llenar las 13 categorías.

## Método de Montecarlo

El jugador `mc` estima el valor de las decisiones probando continuaciones aleatorias para cada objetivo de anotación y conjunto de dados que podría conservar. Luego escoge la opción con mayor utilidad promedio estimada. La estrategia `greedy` decide usando la mano actual, sin simular lanzamientos futuros.

`--samples` controla cuántas continuaciones aleatorias se evalúan por candidato: un número mayor suele reducir el ruido de la estimación y requiere más tiempo. `--seed` fija la semilla para poder repetir el experimento. Los dados se modelan con resultados independientes y equiprobables entre 1 y 6.

El modo `simulate` juega partidas automáticas con Montecarlo como jugador 1 y greedy como jugador 2. El resumen contiene victorias, empates y puntajes medios, mínimos y máximos; se imprime en pantalla y puede guardarse como JSON con `--output`.

### Resultado de referencia

Experimento reproducible con semilla 2026, 100 partidas y 24 muestras por candidato:

| Métrica | Montecarlo | Greedy |
| --- | ---: | ---: |
| Victorias | 53 | 46 |
| Puntaje medio | 215,38 | 214,17 |
| Puntaje mínimo | 130 | 123 |
| Puntaje máximo | 398 | 490 |

Hubo un empate. La diferencia observada es pequeña y describe esta ejecución; por sí sola no demuestra que una política sea mejor en general. El detalle está en [`Act1/resultados.json`](Act1/resultados.json).

## Estructura

```text
Act1/
├── yahtzee.py             # Juego, reglas, estrategias y simulación masiva
├── resultados.json        # Resultados del experimento de referencia
├── informe_tecnico.html   # Informe entregable; se puede imprimir a PDF
├── guia_adaptada.md       # Correspondencia entre consigna y solución
└── README.md              # Instrucciones y descripción de la actividad
```

El [informe técnico](Act1/informe_tecnico.html) documenta introducción, metodología, resultados, conclusiones y referencias. La [guía adaptada](Act1/guia_adaptada.md) registra cómo se atendieron los requisitos de la actividad.

## Referencia

Las reglas de puntuación se basan en el [reglamento oficial de Yahtzee de Hasbro](https://www.hasbro.com/common/instruct/yahtzee.pdf).
