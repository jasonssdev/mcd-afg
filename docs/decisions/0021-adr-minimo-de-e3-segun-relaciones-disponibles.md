# 0021. El mínimo de preguntas validadas de E3 es el menor entre 25 y las relaciones de evolución disponibles

## Estado

Aceptada (2026-11-04), por decisión de `jss`. Resuelve el [issue #276](https://github.com/jasonssdev/mcd-afg/issues/276). Aplica a E3 la regla que [D12](README.md) ya fijó («si E3 no alcanza 25 con las once series de evaluación cerradas, se reporta el número real y no se rellena el cupo»), que el cierre del banco todavía no cumplía. La decisión se toma **antes de que exista cualquier resultado sobre series de evaluación**.

## Contexto

`afg gold questions-check --complete` exige 25 preguntas validadas en cada estrato (`[question_bank].min_questions` en `config/experiments.toml`). En E3 el material no alcanza: las once series de evaluación tienen **24 relaciones de evolución distintas** (24 `pair_id` con `refina`, `revierte` o `reemplaza` en la referencia; [notebook 26](../../notebooks/26-jss-minimo-e3-relaciones-disponibles.ipynb)). Con 24 preguntas E3 válidas el cierre terminaba en error aunque el banco cumpliera D12.

D12 cuenta **relaciones distintas**, no decisiones hijas. Las decisiones hijas de una decisión compuesta no cuentan aparte: son una sola relación adjudicada, y las preguntas que se escriban sobre ellas comparten la evidencia anterior y el `superseded_answer`, de modo que no aportan información independiente. Contarlas inflaría el cupo con preguntas que no son casos distintos.

## Decisión

1. **El mínimo de preguntas validadas de E3 es `min(25, relaciones de evolución disponibles)`.** Los otros tres estratos (E1, E2, E4) siguen en 25.
2. **Relaciones disponibles** son los `pair_id` distintos de las series de evaluación (`[oe1].series` menos `[oe1].development_series`) cuya relación en la **referencia** es `refina`, `revierte` o `reemplaza`. La referencia de cada serie es la que ya resuelve `afg.evaluation.relations.gold_source`: el archivo adjudicado (`final_relation`) o, sin él, el único archivo de un anotador (`relation`). Un `pair_id` cuenta una vez.
3. **El mínimo se calcula desde la referencia, no desde las preguntas validadas.** Una pregunta devuelta en la validación sigue bloqueando el cierre hasta que se reescriba: el mínimo no baja porque falte una pregunta.
4. **`questions-check` y `gold status` usan el mínimo calculado.** Las filas en blanco de E3 desde la posición del mínimo en adelante son opcionales (con 24, las filas de la 25 a la 40), como ya lo eran las que pasan de 25.

## Consecuencias

- **El faltante frente a 25 se informa como limitación de potencia**, no como incumplimiento ni se rellena. Con la simulación del notebook 10 (criterio pareado, dispersión 1, exactitud base de C1 0,5), pasar de 25 a 24 preguntas baja la potencia de 57,5 % a 53,1 % con una mejora verdadera de +0,15 y de 79,5 % a 77,0 % con +0,20; el falso positivo queda en 3,8 %. La conclusión del notebook 10 no cambia.
- **El conteo es un piso del material real**, porque la referencia de relaciones es incompleta por el filtro léxico ([ADR 0020](0020-adr-se-mantiene-el-bloqueador-lexico.md)).
- **Si la referencia cambia** (una adjudicación que modifica una etiqueta, una serie nueva), el mínimo cambia solo; no hay una cifra que actualizar a mano. Si el conteo llega a 25 o más, el mínimo vuelve a 25.
- **No cambia** ninguna anotación, adjudicación, criterio de éxito ni el tope de 40 filas de E3. No agrega trabajo para `gm` ni `gv`.
- Se actualizan las guías `tareas-gm.md` (§7) y `tareas-gv.md` (§8), que decían que llegar a 25 en E3 es obligatorio.

## Respaldo

- Código: `count_evolution_relations`, `load_gold_pair_labels` y `available_evolution_relations` en `src/afg/evaluation/relations.py`; `evolution_minimum`, `stratum_minimums` y `configured_minimums` en `src/afg/experiments/question_bank.py`, que usa `load_configured_question_bank`, y `src/afg/annotation/progress.py` (`afg gold status`).
- Tests: `tests/test_evolution_minimum.py`, escritos antes que el código.
- Análisis: [notebook 26](../../notebooks/26-jss-minimo-e3-relaciones-disponibles.ipynb), con el conteo por serie (24 en total) y la potencia con 24, 25 y 40 preguntas.
