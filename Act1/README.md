# Act1 — Yahtzee y Montecarlo

Programa de consola en Python 3.11 o superior. No requiere paquetes externos. Simula dos jugadores con cinco dados justos de seis caras, hasta tres lanzamientos por turno y 13 turnos por jugador.

## Archivos

- `yahtzee.py`: reglas, juego interactivo, estrategias automáticas y simulación masiva.
- `resultados.json`: salida de referencia con semilla fija.
- `informe_tecnico.html`: documento técnico entregable; abrirlo en un navegador o imprimirlo como PDF.
- `guia_adaptada.md`: relación entre la consigna y la solución; el repositorio inicial no contenía una guía adjunta.

## Ejecutar

Desde la raíz del repositorio:

```powershell
python Act1/yahtzee.py play --player1 human --player2 mc
python Act1/yahtzee.py play --player1 human --player2 human
python Act1/yahtzee.py play --player1 mc --player2 greedy --seed 2026
python Act1/yahtzee.py simulate --games 100 --samples 24 --seed 2026 --output Act1/resultados.json
```

Si Python se instaló con `uv`, se puede reemplazar `python` por `uv run --python 3.12`.

`mc` estima con muestras aleatorias la puntuación futura de cada objetivo de anotación; `greedy` decide según la mano actual. `--samples` determina cuántas muestras usa Montecarlo por candidato. `--seed` permite repetir una ejecución. Durante un turno humano se indican las posiciones de dados a conservar, de 1 a 5, separadas por espacios. Pulsar Enter sin índices termina los lanzamientos y pasa a anotar.

El modo `simulate` enfrenta `mc` como jugador 1 con `greedy` como jugador 2 y produce un resumen JSON. Las muestras Montecarlo y los dados se toman de un generador seudoaleatorio uniforme. La semilla fija sirve para reproducibilidad, no representa aleatoriedad física.

## Reglas implementadas

Se usan las 13 categorías tradicionales. En la sección superior se suman los dados del número elegido y se otorgan 35 puntos al alcanzar 63. Trío y cuarteto suman los cinco dados; full vale 25, escalera corta 30, larga 40, Yahtzee 50 y azar suma los dados. Una categoría se usa una sola vez, incluso si anota cero. Un Yahtzee adicional da 100 puntos cuando la casilla Yahtzee contiene 50. Se aplican las reglas Joker y la prioridad de casillas del reglamento de Hasbro.

Referencia oficial: [reglas de Yahtzee de Hasbro](https://www.hasbro.com/common/instruct/yahtzee.pdf).
