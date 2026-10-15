# 0009. La citación es correcta cuando al menos una cita toca la evidencia de referencia, y la precisión de las citas se informa aparte

## Estado

Aceptada (2026-10-15)

## Contexto

La propuesta de tesis define la métrica en §5.6 (Respuesta OE3):

> «**tasa de citación correcta** (la fuente citada respalda efectivamente la afirmación —
> distinta de la anterior, y la que detecta el modo de falla más peligroso: respuesta correcta
> con cita que no la sustenta)»

y §6.2 fija el criterio de trazabilidad: «Una afirmación sin fuente identificable cuenta como
falla aunque sea correcta.»

El texto habla de «la fuente citada» en singular y no dice qué ocurre cuando una respuesta cita
varias fuentes y solo algunas la respaldan. La primera implementación resolvió el caso sin
decidirlo de forma explícita: la citación era correcta solo si **todas** las citas compartían
reunión y al menos un acto de diálogo con la evidencia de referencia de la pregunta.

La corrida de humo con C1 sobre ES2015 puso esa regla a prueba. Lo medido, con el
[notebook 09](../../notebooks/09-jss-regla-de-citacion.ipynb) (cifras calculadas con
`reference_sizes`, `compare_records` y `tally_variants`; 13 respuestas con evidencia de
referencia, serie de desarrollo):

- La referencia es escasa: **10 de 17** preguntas tienen un único acto de diálogo como
  evidencia, y ninguna pasa de cuatro. En cambio, C1 cita fragmentos completos: la **mediana**
  es de 1 acto de referencia frente a 68 actos citados.
- Con la regla de «todas las citas», la citación se rechaza en 8 de las 13 respuestas, y **7 de
  esas 8 son correctas** según el juez. Con «al menos una cita», se rechazan 4 y **3 correctas**.
- El caso q007 muestra por qué: la respuesta cita el fragmento que contiene el acto señalado y,
  además, un repaso posterior donde el equipo confirma lo mismo. La regla de «todas» lo da por
  incorrecto aunque ambas fuentes respaldan la respuesta; mezcla citar de más con no sustentar.

## Decisión

1. **Regla.** `citation_correct` es verdadero cuando **al menos un** fragmento citado comparte
   reunión y al menos un acto de diálogo con la evidencia de referencia (variante «alguno toca»).
2. **Casos sin cambio.** La métrica no aplica (`None`) a abstenciones, a preguntas E4 y a
   preguntas sin evidencia de referencia. Una respuesta contestada a una pregunta con respuesta
   y sin ninguna cita es falsa, conforme a §6.2.
3. **Cifra secundaria.** Se registra `citation_precision`, la fracción de los fragmentos citados
   que tocan la referencia, con el mismo dominio de aplicación que la regla (`None` donde la
   regla es `None`). Una respuesta sin citas tiene precisión **0,0** y no `None`: §6.2 la
   cuenta como falla, y omitirla del promedio retiraría justamente las respuestas sin fuente.
4. **Una sola fuente de cálculo.** La noción de «tocar» se calcula en
   `afg.evaluation.citation_variants`; `citation_correct` y `citation_precision` la reutilizan.
5. **Registros.** Los registros del runner pasan a `schema_version` 2 y llevan
   `citation_precision`. Los registros de versión 1 (la corrida de humo ya guardada) conservan
   el valor antiguo de `citation_correct`; `rescore_citation` los recalcula con la regla vigente
   a partir de la respuesta y la pregunta guardadas, sin reescribir el archivo, y la ausencia de
   `citation_precision` se lee como desconocida.

## Consecuencias

- **Detecta lo que §5.6 describe.** El modo de falla peligroso es una cita que no sustenta la
  respuesta, es decir, que ninguna fuente citada la respalda; eso es lo que la regla detecta.
  La evidencia de referencia es un piso, no el único lugar donde está el hecho: AMI suele
  enlazar un solo acto por decisión.
- **Se puede ganar citando todo.** Quien cita muchos fragmentos tiene más oportunidades de que
  alguno toque la referencia. Los dos casos con `USED:` en línea de la corrida de humo la pasan
  solo porque citan todos los fragmentos recuperados. La precisión, informada junto a la tasa,
  lo deja a la vista: una citación correcta con precisión baja es sospechosa. Ninguna de las dos
  cifras debe leerse sola.
- **Riesgo de granularidad entre condiciones.** C1 cita fragmentos completos; C2 y C3 citarán
  decisiones, con evidencia más acotada. Una regla de solapamiento de actos puede favorecer a C1
  por ese tamaño y no por la calidad de la fuente. Se declara como riesgo y se **revisará con los
  primeros datos de C2, antes de correr cualquier evaluación**; un cambio de regla se registrará
  antes de ver resultados de las series de evaluación.
- **Las cifras de la corrida de humo cambian al releerlas.** Bajo la regla nueva, 9 de las 13
  citaciones son correctas. Siguen siendo cifras de desarrollo (ADR 0005) y no entran en ninguna
  tabla de resultados.
- **La variante «todos tocan» y la cobertura** quedan en `citation_variants` solo para comparar.

## Trazabilidad

- Evidencia: [notebook 09](../../notebooks/09-jss-regla-de-citacion.ipynb), con las cuatro
  variantes lado a lado, la tabla de opciones y tres casos; y el
  [notebook 07](../../notebooks/07-jss-runner-experimento-b.ipynb), que relee la corrida de
  humo con la regla nueva.
- Código: `src/afg/evaluation/citation.py` (`citation_correct`, `citation_precision`),
  `src/afg/evaluation/citation_variants.py`, `src/afg/experiments/citation_analysis.py`
  (`rescore_citation`) y `src/afg/experiments/runner.py`; pruebas en `tests/test_citation.py`,
  `tests/test_citation_variants.py`, `tests/test_citation_analysis.py`,
  `tests/test_experiment_b_runner.py` y `tests/test_experiment_b_summary.py`.
- Metodología: [`../avances/06-jss-metodologia.md`](../avances/06-jss-metodologia.md) v3.3.
- Se apoya en el [ADR 0005](0005-adr-development-evaluation-split.md) (las cifras de desarrollo
  no son resultados).
