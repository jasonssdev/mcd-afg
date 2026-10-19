# 0012. El umbral τ principal del Experimento A es 0,70, con 0,75 y 0,80 como sensibilidad, por desvío de la regla prerregistrada

## Estado

Aceptada (2026-10-19). Fija el umbral τ que el [ADR 0011](0011-adr-alineacion-rol-e-intervalos-del-experimento-a.md) dejó abierto y resuelve la elección de τ del [issue #142](https://github.com/jasonssdev/mcd-afg/issues/142). **Desvía de una regla prerregistrada** (`τ = max(τ_nulo, τ_juez)`, que daba 0,80); el desvío se declara abajo. La concordancia entre el juez y una persona queda **pendiente** (sin anotador asignado).

## Contexto

El Experimento A cuenta una decisión extraída como acierto cuando su similitud con una decisión de referencia es al menos τ ([protocolo de alineación](../protocols/alignment.md)). Ni el ADR 0011 ni el [notebook 15](../../notebooks/15-jss-screen-de-modelos-openkos.ipynb) fijaron τ, y la versión 2.0 del protocolo cambió el texto de referencia a su traducción al inglés, lo que desplaza toda la curva: τ debía fijarse después de esa traducción.

El [notebook 17](../../notebooks/17-jss-tau-referencia-en.ipynb) reúne los insumos sobre las 100 corridas guardadas de `reports/experiment-a/model-screen-openkos/` (ES2015 y TS3009, **series de desarrollo**, [ADR 0005](0005-adr-development-evaluation-split.md); no se generó ninguna extracción nueva). Antes de mirar los resultados se fijaron dos criterios y una regla de combinación:

- **Criterio A, control nulo.** Se puntúa la salida de una serie contra la referencia de la otra, reunión a reunión y en los dos sentidos; `τ_nulo` es el menor τ de la grilla con cobertura nula media ≤ 0,05.
- **Criterio B, juez.** Una muestra de 200 pares emparejados (similitud en [0,50; 0,90), bins de 0,05, 25 por bin, semilla 42) la juzga `gpt-oss:20b` con el prompt `same-decision-v1` («¿describen ambos textos la misma decisión?»); `τ_juez` es el menor límite de bin desde el cual la proporción de «sí» supera 0,5 en ese bin y en todos los superiores.
- **Regla.** `τ = max(τ_nulo, τ_juez)`; la curva completa se sigue informando.

Resultado de los criterios: `τ_nulo` = 0,80 y `τ_juez` = 0,70, de modo que la regla daba **0,80**.

## Decisión

1. **τ principal = 0,70** para la alineación del Experimento A con la referencia en inglés.
2. **τ = 0,75 y τ = 0,80 se informan siempre como análisis de sensibilidad**, al lado del principal.
3. **La curva completa sobre `tau_grid`** sigue informándose, tal como exige el paso 4 del protocolo: τ = 0,70 es el punto de lectura, no el reemplazo de la curva.
4. **El juez complementa la validación manual del protocolo, no la sustituye.** Una comprobación de concordancia entre el juez y una persona sobre 50 pares de la muestra juzgada queda **pendiente**. No existen aún archivos de anotación para ella.

## Desvío de la regla prerregistrada

La regla fijada antes de ver los resultados daba τ = 0,80. Esta decisión **se aparta de ella** y lo hace después de conocer los resultados, lo que obliga a decir por qué.

**Razón: un defecto del control nulo, descubierto al aplicarlo.** El control nulo cruza dos equipos de AMI (ES2015 y TS3009) que recibieron **el mismo encargo de diseño**: el mismo precio de venta (25 €), el mismo costo (12,50 €) y la misma tecnología de teletexto. Parte de las coincidencias que el control cuenta como «azar» son, por lo tanto, **la misma decisión de verdad**, tomada por dos equipos que partían del mismo encargo. El piso nulo está sobrestimado, y `τ_nulo` = 0,80 mide en parte un parecido legítimo y no solo coincidencia temática. Esa sobrestimación no se midió: no se sabe qué fracción de las coincidencias nulas es la misma decisión; la lectura se apoya en el encargo compartido, no en un cálculo.

**Qué no es la razón.** No se elige 0,70 por dar mejores resultados. Que con 0,70 la cobertura sea mayor es una consecuencia (ver abajo), no el motivo, y quien lea esta decisión debe poder separar ambas cosas: el criterio A se descarta como regla por un defecto de su construcción, y el criterio B (que ya daba 0,70) pasa a ser el que decide. La coincidencia entre 0,70 y el valor que más cobertura deja es una limitación declarada, no una prueba a favor.

## Evidencia

Todas las cifras salen del notebook 17 (confirmatoria y *screen*, 100 corridas, referencia en inglés; desarrollo).

### Control nulo (cobertura nula media)

| τ | 0,60 | 0,65 | 0,70 | 0,75 | 0,80 |
|---|---|---|---|---|---|
| Referencia en inglés | 0,570 | 0,285 | 0,138 | 0,053 | 0,015 |

Con τ = 0,75 el piso queda a 0,003 del tope de 0,05; la regla dependía de ese margen. Con la referencia en español `τ_nulo` habría sido 0,70, así que la traducción sube el piso un paso de la grilla.

### Juez (proporción de «sí» por bin, 25 pares por bin)

| Bin | [0,50; 0,55) | [0,55; 0,60) | [0,60; 0,65) | [0,65; 0,70) | [0,70; 0,75) | [0,75; 0,80) | [0,80; 0,85) | [0,85; 0,90) |
|---|---|---|---|---|---|---|---|---|
| «Sí» | 0,12 | 0,24 | 0,28 | 0,32 | 0,80 | 0,76 | 0,92 | 0,92 |

Por debajo de 0,70 la proporción de «sí» es a lo más 0,32; desde 0,70, al menos 0,76 en todos los bins. Los intervalos de Wilson de [0,65; 0,70) (0,17 a 0,52) y [0,70; 0,75) (0,61 a 0,91) no se solapan. Las 200 respuestas fueron legibles.

### Lo que deja cada τ (confirmatoria, 15 corridas; cobertura real frente a nula 0,138 con 0,70 y 0,015 con 0,80)

| Modelo y serie | τ = 0,70 | τ = 0,80 |
|---|---|---|
| `qwen3.6:27b`, ES2015 | 0,467 | 0,079 |
| `qwen3.6:27b`, TS3009 | 0,613 | 0,200 |
| `qwen3:8b`, ES2015 | 0,338 | 0,111 |
| `qwen3:8b`, TS3009 | 0,436 | 0,138 |

Con τ = 0,80 el instrumento casi deja de encontrar decisiones reales, y los pares entre 0,70 y 0,80, que el juez aprueba en 39 de 50 casos, quedarían fuera. Se cita como contexto de la sensibilidad, no como motivo del desvío.

## Alternativas descartadas

- **τ = 0,80, la regla tal como se prerregistró.** Cumple los dos criterios, pero su criterio A se apoya en un control con un defecto conocido (encargo compartido) y deja una cobertura real de 0,08 a 0,20 en `qwen3.6:27b`. Se conserva como sensibilidad.
- **τ = 0,75.** Intermedio: el azar vale 0,053, 0,003 sobre el tope. Se conserva como sensibilidad; no se elige porque el tope de 0,05 sería entonces un criterio de lectura y no una regla, y el juez ya respalda 0,70.
- **Reemplazar la validación manual por el juez.** El juez es un modelo, no una persona: su «sí» en 0,576 del notebook 17 es discutible, y su concordancia con una anotación humana no se ha medido. Complementa; no sustituye.
- **Corregir el control nulo antes de decidir** (por ejemplo, con una serie de otro encargo). Mejoraría el piso, pero exige un control con series de otro encargo y su propia calibración; no se hizo para esta decisión y queda como mejora posible.

## Consecuencias

- **Protocolo.** [`docs/protocols/alignment.md`](../protocols/alignment.md) pasa a la versión 3.0: fija τ principal y sensibilidades y declara el papel del juez. El procedimiento (pasos 1 a 4) no cambia; la validación manual de al menos 100 pares (`manual_validation_sample_size`) se mantiene, porque mide otra cosa (alineación automática frente a emparejamiento manual) que la comprobación pendiente de 50 pares (juez frente a persona).
- **Informes.** Todo informe del Experimento A da la cobertura y el F1 con τ = 0,70 como principal, con 0,75 y 0,80 al lado y la curva completa, junto con el piso nulo de cada τ (0,138, 0,053 y 0,015).
- **Configuración.** `config/experiments.toml` no tiene una clave de τ principal (solo `tau_grid` y `manual_validation_sample_size`), y no se crea una: τ principal vive en este ADR y en el protocolo. El código que puntúa recorre la grilla.
- **Limitaciones declaradas.** (1) La elección se hizo después de ver los resultados, apartándose de una regla prerregistrada. (2) El piso nulo está sobrestimado por una cantidad no medida. (3) El juez es un solo modelo, con 25 pares por bin sacados de dos series de desarrollo y cuatro modelos `qwen3`; los pares comparten decisiones de referencia entre modelos y corridas. (4) El τ sale de series de desarrollo; se aplica sin cambios a las series de evaluación.
- **Pendiente.** Concordancia entre `gpt-oss:20b` y una persona sobre 50 pares de la muestra juzgada (anotador por asignar). Si arroja un acuerdo bajo, esta decisión se revisa con un ADR que la reemplace.
- **Sin cambios.** La regla de citación ([ADR 0009](0009-adr-regla-de-citacion-correcta.md)), el criterio D16 ([ADR 0010](0010-adr-decisiones-del-analisis-del-experimento-b.md)), el ámbito, el rol y los intervalos del ADR 0011 y los demás umbrales.

## Trazabilidad

| Afirmación | Dónde se verifica |
|---|---|
| Cobertura nula por τ; `τ_nulo` = 0,80 | [`notebooks/17-jss-tau-referencia-en.ipynb`](../../notebooks/17-jss-tau-referencia-en.ipynb) §3.1; `src/afg/experiments/tau_calibration.py` (`null_curve_points`, `null_coverage`, `tau_null`); `tests/test_tau_calibration.py` |
| Proporción de «sí» por bin; `τ_juez` = 0,70 | Notebook 17 §3.2 y §3.3; `tau_calibration.py` (`matched_pairs`, `stratified_sample`, `judge_sample`, `bin_table`, `tau_judge`); respuestas crudas, digest y hash del prompt en [`reports/experiment-a/tau-calibration/`](../../reports/experiment-a/tau-calibration/PROCEDENCIA.md); prompt `src/afg/evaluation/prompts/same_decision_v1.md` |
| Regla prerregistrada y su resultado (0,80) | Notebook 17 §4; `tau_calibration.py` (`propose_tau`) |
| Cobertura real por τ y desplazamiento por la referencia en inglés | Notebook 17 §2 y §4; `src/afg/experiments/model_screen.py` (`score_curve`, `curve_summary`) |
| Encargo compartido por los dos equipos (precio, costo, teletexto) | Lectura del control nulo; no se mide en el notebook (ver Desvío) |
| ES2015 y TS3009 son series de desarrollo | [ADR 0005](0005-adr-development-evaluation-split.md) |
| Grilla de τ | `config/experiments.toml`, `[alignment].tau_grid` |
| Protocolo 3.0 y metodología 6.0 | [`docs/protocols/alignment.md`](../protocols/alignment.md); [`docs/avances/06-jss-metodologia.md`](../avances/06-jss-metodologia.md) |
