# 0011. El Experimento A se puntúa con la reunión de origen como ámbito, el rol mayoritario y un bootstrap por reuniones como intervalo principal

## Estado

Aceptada (2026-10-16). Cierra el [issue #99](https://github.com/jasonssdev/mcd-afg/issues/99). Ratifica dos valores que la metodología (versión 3.5) dejó como provisionales y cambia el intervalo principal de los resultados agrupados. **No fija el umbral τ.**

## Contexto

El código de puntuación del Experimento A (`afg.evaluation.scoring`, `afg.evaluation.reference`) dejó dos decisiones metodológicas con un valor por defecto provisional, y una limitación declarada:

1. **Ámbito de la alineación.** Una decisión extraída puede emparejarse con una decisión de referencia de su reunión de origen (estricto) o con cualquiera de la serie (permisivo). OpenKOS puede reunir en un solo concepto una decisión repetida en varias reuniones, así que el protocolo (`docs/protocols/alignment.md`) no basta para elegir.
2. **Rol del hablante** de una decisión de referencia con evidencia de varios roles: el rol mayoritario (empate: el turno más temprano) o cada rol involucrado.
3. **Intervalos.** Wilson para precision y recall y bootstrap por decisión para F1 tratan las decisiones como independientes e ignoran su agrupación por reunión y serie.

El análisis es el [notebook 14](../../notebooks/14-jss-alineacion-experimento-a.ipynb), sobre la primera extracción real de una serie de desarrollo: ES2015, tres corridas de OpenKOS 0.5.5 (`es2015-explora-r3x`), a lo largo de toda la grilla `tau_grid` de `config/experiments.toml`. ES2015 es una serie de **desarrollo** ([ADR 0005](0005-adr-development-evaluation-split.md)): ninguna de sus cifras es un resultado ni entra en una tabla de resultados, y OpenKOS 0.5.5 es provisional. El análisis ofrece insumos y no decide; estas decisiones las tomó jss el 2026-10-16 a partir de ellos.

## Decisión

1. **Ámbito de la alineación.** El ámbito **principal** son las **reuniones de origen**: una decisión extraída solo se empareja con decisiones de referencia de su reunión (o reuniones) de origen (`alignment_scope="origin_meetings"`). La alineación sobre **toda la serie** (`alignment_scope="series"`) es la **sensibilidad** y se informa siempre al lado. Es el comportamiento que ya tenía el código; se ratifica, no cambia.
2. **Rol de una decisión con evidencia de varios roles.** El **rol mayoritario** (el que más habló; empate: el turno más temprano) es el **principal**. Contar la decisión en **cada rol involucrado** es la **sensibilidad**. Es el comportamiento actual; se ratifica, no cambia.
3. **Intervalos.** El intervalo **principal** de precision, recall y F1 de los resultados agrupados del Experimento A pasa a ser un **bootstrap percentil que remuestrea reuniones completas** (`afg.evaluation.scoring.meeting_cluster_intervals`), con los remuestreos, el nivel y la semilla de `config/experiments.toml`, de modo que es determinista. El intervalo de **Wilson** (precision, recall) y el **bootstrap por decisión** (F1) se conservan como **referencia** y se informan al lado (`*_interval_reference`).
4. **Limitación declarada.** Con pocas reuniones el bootstrap por reuniones es burdo: una serie suelta como ES2015 tiene 4 reuniones, lo que da solo 35 remuestreos distintos, y su intervalo es frágil (a veces se degenera). Se estabiliza al agrupar varias series de evaluación.
5. **τ no se decide aquí.** No hay un τ único fijado; el análisis se hace sobre `tau_grid` y cualquier valor de τ se decide con otra evidencia, sobre series de desarrollo.

## Evidencia

Todas las cifras salen del notebook 14 (ES2015, tres corridas agrupadas, desarrollo).

### Ámbito

F1 agrupado por ámbito, con la grilla de τ:

| τ | F1 misma reunión (principal) | F1 toda la serie (sensibilidad) |
|---|---|---|
| 0,50 | 0,43 | 0,56 |
| 0,60 | 0,29 | 0,43 |
| 0,70 | 0,07 | 0,09 |

Desde τ = 0,80 ambos valen 0: ningún par (objeto, contenido) alcanza esa similitud, porque la extracción está en inglés y la referencia en español. La toda-la-serie da cifras mayores o iguales en todo τ, así que el orden entre ámbitos no cambia y la elección de τ pesa más que la del ámbito (dentro de un mismo ámbito, F1 pasa de 0,43 a 0,07 entre τ = 0,50 y 0,70).

Con τ = 0,60, la serie completa logra 7 emparejamientos más por corrida (un 50 %) y entre 9 y 12 de sus pares cruzan reuniones. Se leyeron 12 de esos cruces (corrida 0): unos 8 (alrededor de dos tercios) son **re-enunciados legítimos**, la misma decisión retomada en una reunión posterior, y unos 4 (alrededor de un tercio) son débiles o espurios. La lectura es cualitativa y no se midió qué fracción es de cada tipo. La **similitud no separa** unos de otros: la mediana de los cruces (0,65) es solo algo menor que la de los pares de la misma reunión (0,68).

Por eso conviene una regla estricta como principal, que no reconoce un re-enunciado legítimo pero nunca cuenta un cruce espurio, y la permisiva como sensibilidad, que deja ver cuánto depende el resultado del ámbito. Ninguna variante resuelve por sí sola si una decisión re-enunciada es acierto o repetición.

### Rol

El cargador de referencia encuentra **6 de las 27** decisiones de ES2015 con evidencia de más de un rol (21 con un rol, 5 con dos y 1 con tres). El [issue #99](https://github.com/jasonssdev/mcd-afg/issues/99) mencionaba 9 de 27; esa cifra **no se pudo reproducir** con el cargador actual y no se usa. Contar la decisión en cada rol sube los denominadores de 27 a 34 y mueve poco la cobertura por rol: con τ = 0,60 y misma reunión, ME pasa de 0,50 a 0,57 y PM de 0,47 a 0,53, y ID y UI no cambian; con toda la serie los cambios van de −0,01 a +0,07. El efecto es de a lo más 0,07, con roles que tienen entre 1 y 19 decisiones de referencia por corrida. El rol mayoritario es simple y mantiene el denominador; contar cada rol refleja que la evidencia involucra a varias personas, a costa de contar una decisión más de una vez, y queda como sensibilidad.

### Intervalos

Con τ = 0,60, ancho del intervalo del 95 % (estándar: Wilson / bootstrap por decisión; por reunión: bootstrap por reuniones):

| ámbito | métrica | ancho estándar | ancho por reunión | razón |
|---|---|---|---|---|
| misma reunión | precision | 0,108 | 0,100 | 0,9 |
| misma reunión | recall | 0,213 | 0,477 | 2,2 |
| misma reunión | F1 | 0,121 | 0,184 | 1,5 |
| toda la serie | precision | 0,123 | 0,222 | 1,8 |
| toda la serie | recall | 0,182 | 0,429 | 2,4 |
| toda la serie | F1 | 0,134 | 0,269 | 2,0 |

El intervalo por reuniones es de 1,5 a 2,4 veces más ancho en recall y F1: las reuniones aportan entre 4 y 8 decisiones de referencia y varían mucho en lo bien que se extraen, algo que Wilson no ve. La precision de la misma reunión es la excepción, porque hay muchas decisiones extraídas por reunión. Los intervalos estándar de las cifras agrupadas son además más angostos de lo debido, porque cuentan tres veces las mismas reuniones. Con cuatro reuniones el bootstrap por reuniones es burdo (35 remuestreos distintos): en algunos casos se degenera (con toda la serie y τ = 0,50 el recall vale 1,00 en todas las remuestras). El orden de magnitud es informativo; el valor puntual de cada ancho, no.

## Alternativas descartadas

- **Toda la serie como ámbito principal.** Da cifras mayores, pero cuenta como acierto cruces que, en la lectura, son espurios en alrededor de un tercio, y la similitud no los separa. Se conserva como sensibilidad.
- **Contar cada rol como principal.** Cambia la cobertura por rol en menos de 0,08, cuenta la misma decisión más de una vez e infla los denominadores (34 frente a 27), sin cambiar ninguna lectura. Se conserva como sensibilidad.
- **Solo declarar la limitación de los intervalos estándar.** Deja como principal un intervalo que, para recall y F1, subestima la incertidumbre en un factor cercano a dos. Se prefiere cambiar el principal y conservar el estándar como referencia.
- **Fijar ahora un τ.** Las cifras caen casi a cero desde τ = 0,75 por la diferencia de idioma entre la extracción y la referencia, y una sola serie de desarrollo no basta; se decide con otra evidencia.

## Consecuencias

- **Código.** `pool_scores` y `score_runs` entregan en `precision_interval`, `recall_interval` y `f1_interval` el bootstrap por reuniones (cada `SeriesScore` registra la reunión de cada decisión extraída y de referencia), con `n_clusters`, y en `*_interval_reference` los intervalos de Wilson y por decisión; `interval_methods` y `reference_interval_methods` rotulan cada método. `meeting_cluster_intervals` vive en `scoring.py`; `alignment_analysis.py` la reexporta para el notebook 14. Los valores por defecto de ámbito y rol no cambian.
- **Metodología.** Pasa a la versión 4.0 (cambia una decisión: el intervalo principal): ratifica las dos decisiones que la 3.5 dejó como provisionales, declara el intervalo principal por reuniones y su limitación.
- **Un informe de resultados** del Experimento A informa, siempre: el ámbito principal con la serie completa al lado, el rol mayoritario con cada rol al lado, y el intervalo por reuniones con el de referencia al lado.
- **Series sueltas.** El intervalo principal de una serie sola (4 reuniones) es frágil y se declara así; los resultados reportables agrupan las series de evaluación (ADR 0005).
- **Sin cambios.** El umbral τ, la regla de citación ([ADR 0009](0009-adr-regla-de-citacion-correcta.md)), el criterio D16 ([ADR 0010](0010-adr-decisiones-del-analisis-del-experimento-b.md)) y los demás umbrales quedan como estaban. Ninguna cifra de ES2015 de este ADR es un resultado (serie de desarrollo, OpenKOS 0.5.5 provisional).

## Trazabilidad

| Afirmación | Dónde se verifica |
|---|---|
| F1 por ámbito y τ; cruces entre reuniones; efecto del rol; anchos de intervalo | [`notebooks/14-jss-alineacion-experimento-a.ipynb`](../../notebooks/14-jss-alineacion-experimento-a.ipynb) |
| Ámbito, rol y bootstrap por reuniones | `src/afg/evaluation/scoring.py` (`score_series`, `score_series_views`, `pool_scores`, `meeting_cluster_intervals`); `src/afg/evaluation/alignment_analysis.py`; `tests/test_scoring.py`, `tests/test_alignment_analysis.py` |
| 6 de 27 decisiones de ES2015 con varios roles | `src/afg/evaluation/reference.py` (`roles_of`, `primary_role`); notebook 14 §3 |
| Grilla de τ sin valor único | `config/experiments.toml`, `tau_grid` |
| ES2015 es una serie de desarrollo | [ADR 0005](0005-adr-development-evaluation-split.md) |
| Metodología 4.0 | [`docs/avances/06-jss-metodologia.md`](../avances/06-jss-metodologia.md) §1 y §7–8 |
