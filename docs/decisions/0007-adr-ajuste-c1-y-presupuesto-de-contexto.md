# 0007. C1 se ajusta a 8 fragmentos de hasta 1.600 caracteres, y las condiciones comparten el presupuesto de texto, no el número de bloques

## Estado

Aceptada (2026-10-15)

## Contexto

La sección 5.3 de la tesis exige que C1 sea una línea base **honesta**: tamaño de fragmento y
número de fragmentos recuperados (K) ajustados sobre datos de desarrollo, y no heredados sin
evidencia. El [ADR 0006](0006-adr-c1-rag-separado-con-respuesta-de-openkos.md) dejó ese ajuste
pendiente. Además, la sección exige un presupuesto de contexto compartido entre C1, C2 y C3.

C2 y C3 responden con `openkos query`, cuyo `--limit` vale 5 por defecto. Ese valor no tiene
justificación documentada: apareció como valor inicial en el commit `27a71a7d` de OpenKOS
(2026-07-18, PR #29). Lo que sí está medido es el presupuesto de *prompt* de OpenKOS v0.5.4:
reserva 4.096 *tokens* para el contexto (`PROMPT_CONTEXT_ALLOWANCE`) y midió que 5 cuerpos
ocupan 13.516 caracteres, unos 3.263 *tokens*, con una ventana de 12.288 *tokens*
(`DEFAULT_CONTEXT_WINDOW`).

Un «bloque» no significa lo mismo en cada condición: en C1 es un fragmento de transcripción;
en C2 y C3 es un concepto compilado. Igualar el número de bloques no iguala lo que el modelo
lee.

## Decisión

1. **Ajuste prerregistrado.** Se fijó la regla antes de correr (commit `cfce5af`): rejilla
   `max_chars` ∈ {800, 1200, 1600, 2400} × `overlap_turns` ∈ {0, 1} × K ∈ {3, 5, 8, 10};
   elegible si K × `max_chars` ≤ 13.516; gana el elegible de mayor recall de evidencia
   medio; a ≤ 0,02 del mejor se prefiere menor K, luego menor `max_chars`, luego
   `overlap_turns` 0. Se midió solo la recuperación (sin modelo generativo) sobre las 17
   preguntas respondibles de ES2015 (14 E1, 2 E2, 1 E3), con el índice de las cuatro
   reuniones de la serie (D15).
2. **C1 usa `max_chars` = 1.600, `overlap_turns` = 0 y K = 8.** Recall medio de 0,642; el
   mejor elegible (0,657, con 1.200 / 1 / 10) queda dentro del margen y pierde por la regla
   de desempate. La configuración de mayor recall de toda la rejilla (2.400 / 1 / K = 8,
   0,706) no es elegible: admite hasta 19.200 caracteres (17.900 de media), más que el presupuesto. Los
   parámetros quedan fijados en `[retrieval.c1]` de
   `config/experiments.toml`, y una prueba verifica que coinciden con el ganador almacenado.
3. **Presupuesto de texto igual, no K igual (opción A).** C1 envía 8 fragmentos (unos 12.000
   caracteres de contexto medio); C2 y C3 mantienen `openkos query --limit 5` (unos 13.500
   caracteres, el presupuesto que OpenKOS midió). Lo que el modelo lee es texto, y los dos
   totales son comparables.
4. **Opción B, un K común, se descarta.** Con K = 8 para C2 el contexto sería de unos 21.600
   caracteres, más allá de lo que OpenKOS midió como cabida del *prompt*: se truncaría el
   contexto o se reduciría el espacio de la respuesta, y la diferencia entre condiciones
   dependería del recorte y no de la representación. Con K = 5 para C1 se pierde recall
   medible (0,583 frente a 0,642) sin ganar equivalencia real.
5. **No se cambia el valor por defecto de OpenKOS.** `--limit` es una opción pública y el
   [ADR 0006](0006-adr-c1-rag-separado-con-respuesta-de-openkos.md) se respeta. Si más
   adelante los datos muestran que 5 es insuficiente para C2, se propondrá su cambio en
   OpenKOS con evidencia, no se alterará para la tesis.

## Consecuencias

- La línea base C1 queda ajustada con una regla fijada antes de ver resultados, como exige
  §5.3, y reproducible desde `reports/c1-tuning/resultados.json`.
- `answer_limit = 5` en `config/experiments.toml` pasa a significar «`--limit` de C2 y C3»
  y se conserva a propósito; el K de C1 vive aparte en `[retrieval.c1]`.
- La siguiente tarea, `src/afg/conditions/c1_document_rag.py`, lee estos parámetros con
  `load_pinned_c1_params`.
- El informe de resultados debe presentar la igualdad como de **presupuesto de texto**, no
  de número de bloques.

## Limitaciones

- **Una sola serie y 17 preguntas.** El recall de evidencia se midió sobre ES2015; la
  diferencia entre configuraciones cercanas (0,642 frente a 0,657) está dentro del ruido.
  Por eso el margen de 0,02 favorece la configuración más barata.
- **El recall es un piso.** AMI enlaza con frecuencia un solo acto por respuesta
  (`summlink`). Por ejemplo, para «¿Qué fuente de energía se eligió?» (q016) solo se enlaza
  el resumen del jefe de proyecto «Energy, we've decided on kinetic, right?»
  (`ES2015c.A.dialog-act.dharshi.198`), mientras la decisión se discute en muchos otros
  turnos. Un fragmento recuperado puede contener la respuesta sin contener ese acto, y
  contar como fallo. Cinco preguntas no tienen ningún acierto con el ganador (q026, q016,
  q030, q010, q011).
- **Presupuesto en caracteres, no en *tokens*.** La restricción K × `max_chars` usa
  caracteres; no se midieron *tokens* de las transcripciones, que pueden tokenizarse de otra
  forma que los conceptos compilados.
- **El presupuesto de C2 se supone** a partir de la medición de OpenKOS (5 cuerpos =
  13.516 caracteres); debe verificarse cuando se ejecute C2.
- Se midió solo recuperación; el efecto sobre la corrección de las respuestas queda para el
  Experimento B.

## Trazabilidad

- Notebook: [`06-jss-ajuste-c1.ipynb`](../../notebooks/06-jss-ajuste-c1.ipynb).
- Resultados: `reports/c1-tuning/resultados.json`.
- Regla prerregistrada: commit `cfce5af` (`[retrieval.tuning]` en `config/experiments.toml`).
- Código: `src/afg/conditions/c1_tuning.py`; prueba de los parámetros fijados en
  `tests/test_c1_tuning.py`.
- Complementa el [ADR 0006](0006-adr-c1-rag-separado-con-respuesta-de-openkos.md) y se apoya
  en el [ADR 0005](0005-adr-development-evaluation-split.md) (ajuste solo en desarrollo).
