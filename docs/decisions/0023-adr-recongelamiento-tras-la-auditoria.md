# 0023. Se vuelve a congelar tras la auditoría previa a la primera corrida formal

## Estado

**Reemplazada por el [ADR 0024](0024-adr-hoja-oe4-autocontenida.md) (2026-11-05)**: la hoja de OE4 no era autocontenida para quien etiqueta. El texto que sigue se conserva como estaba cuando se aceptó.

Aceptada (2026-11-05), por decisión de `jss`. **Reemplaza al [ADR 0022](0022-adr-congelamiento-de-las-corridas-formales.md)** y resuelve de nuevo el [issue #237](https://github.com/jasonssdev/mcd-afg/issues/237). Mantiene la regla del [ADR 0005](0005-adr-development-evaluation-split.md): nada se ajusta ya con las series de evaluación. La decisión se toma **antes de que exista cualquier corrida formal**.

## Contexto

Después de aceptar el ADR 0022 y antes de correr nada sobre las series de evaluación, se auditó el repositorio entero. **No existía ninguna corrida formal, de modo que ningún resultado se invalida.** La auditoría encontró defectos que habrían dañado o debilitado esas corridas, en cuatro grupos:

1. **Errores que dañaban un resultado.** El análisis del Experimento B exigía 25 preguntas en todo estrato: con las 24 de E3 ([ADR 0021](0021-adr-minimo-de-e3-segun-relaciones-disponibles.md)) los veredictos de D16, H2 y H4 salían «muestra insuficiente». La hoja de OE4 mezclaba corridas y condiciones. `afg experiment b` aceptaba `--limit-questions`, particiones mixtas y reanudar con otro banco. Los informes no comprobaban la corrida contra el registro. `afg c3 build` dejaba un espacio parcial si fallaba.
2. **Huecos del congelamiento.** El registro del ADR 0022 no cubría las transcripciones, `config/corpus.toml`, `config/annotation.toml` ni `.python-version`, y permitía variables `AFG_*` o un `--runs` que cambian el resultado sin cambiar ningún archivo congelado. Los manifiestos no registraban qué congelamiento los produjo.
3. **Protocolo.** La validación manual de la alineación (paso 3 del protocolo) estaba pensada para una sola serie y su clave se guardaba en el repositorio; no existía un protocolo de fallas y repeticiones ni guías para las personas que etiquetan.
4. **Textos.** Ayudas y comentarios de configuración decían que las series de evaluación se rechazaban o que había código pendiente, y varios documentos conservaban cifras superadas (≈ 37 preguntas de E3, 6 de 14 series).

Las correcciones del código y la configuración están en los PR [#283](https://github.com/jasonssdev/mcd-afg/pull/283), [#284](https://github.com/jasonssdev/mcd-afg/pull/284) (fuentes de prueba completas en los tests del banco congelado) y [#285](https://github.com/jasonssdev/mcd-afg/pull/285) (la hoja de OE4 resuelve la base de C2 por la serie de cada pregunta, porque la corrida formal cubre las once series en una sola corrida). Como cambian `src/` y `config/`, el registro del ADR 0022 deja de ser válido: hay que congelar de nuevo, y se aprovecha para dejar por escrito lo que antes quedaba implícito.

## Decisión

Se congela lo mismo que en el ADR 0022 (referencia de las 14 series, banco de 99 preguntas, `config/experiments.toml`, entorno fijado, τ = 0,70, parámetros de C1 y código), **con los cambios siguientes**. El ADR 0022 deja de regir.

### 1. Qué se congela además

- **Transcripciones** (`data/interim/transcripts`, fuera de git): número de archivos (342) y una huella única calculada sobre las rutas ordenadas y la huella de cada archivo.
- **`config/corpus.toml` y `config/annotation.toml`**, cada uno con su huella.
- **`.python-version`**, dentro de las rutas de código (`src`, `pyproject.toml`, `uv.lock`).
- **Reglas de ejecución en evaluación.** Se rechazan `AFG_GENERATIVE_MODEL`, `AFG_JUDGE_MODEL`, `AFG_EMBEDDING_MODEL`, `AFG_SEED` y `AFG_OPENKOS_EXECUTABLE` (en el entorno o en `.env`) y un `--runs` distinto de `runs_per_config`.
- **Esquema del registro: 2.** Un registro del esquema 1 ya no se lee. Los manifiestos de las corridas registran el ADR, el commit y la huella del congelamiento que las produjo.

Las huellas de cada archivo **no se repiten en este ADR**: viven en `config/freeze.json`, que es la fuente de verdad. Solo se dejan las dos que identifican el material de las preguntas:

| Archivo | SHA-256 |
|---|---|
| `data/processed/questions/banco-preguntas.csv` | `d6b7d6bbb80415128967b7e9efc6f46eff6dfd1ce3d5ae23fc6f0f0adb2a0cc5` |
| `config/experiments.toml` (calculada sobre la rama de este ADR) | `f7f9daed2cce615a5b9ca31a83be2fbd9678b2def17135400a9667dc98fa7a59` |

El banco es el mismo del ADR 0022 (99 preguntas: E1 25, E2 25, E3 24, E4 25). `config/experiments.toml` cambió respecto al ADR 0022 solo en comentarios (textos de ayuda que ya no decían que las series de evaluación se rechazaban), no en ningún valor.

### 2. Análisis y hojas

- **Mínimo por estrato en el análisis.** El análisis del Experimento B usa el mínimo del banco por estrato (25 en E1, E2 y E4; 24 en E3), no 25 fijo.
- **Hoja de OE4 por corrida.** Una fila por (pregunta, corrida), solo de C2, con la columna `corrida`; la base de C2 se resuelve por la serie de cada pregunta, así que una corrida con varias series produce una sola hoja.
- **`--questions` obligatorio** en `b-oe4-sheet` y `b-sample`, y debe ser el archivo con el que se corrió.

### 3. Los informes verifican la corrida contra el registro

`a-report`, `b-report`, `b-sample`, `b-oe4-sheet` y `final-tables` comprueban en evaluación que el manifiesto de la corrida coincide con el registro: huella del banco, árbol de trabajo limpio durante la corrida y código. **La regla del código es «mismo commit, o ninguna diferencia en `src`, `pyproject.toml`, `uv.lock` y `.python-version` entre el commit de la corrida y el congelado»**, y no solo «mismo commit», porque `config/freeze.json` se agrega después del commit congelado, en un PR aparte: una corrida hecha con ese archivo ya presente está en un commit distinto sin que el código haya cambiado.

### 4. Validación manual de la alineación

Se hace sobre la corrida de evaluación del Experimento A (repetición 0) con las **once series de evaluación juntas**: los pares candidatos se agrupan y se sortean **100 pares** con la semilla **42** (mitad entre los emparejados por la alineación automática y mitad entre descartados con similitud de al menos 0,50). La hoja lleva la columna `serie`. **La clave queda fuera del repositorio** (`data/interim/alignment-validation/`) y el puntaje se escribe en `reports/`. Si el conjunto tiene menos de 100 pares, el comando se niega. Guía: [`validacion-manual-alineacion.md`](../anotacion/validacion-manual-alineacion.md).

### 5. Quién etiqueta, y bajo qué condiciones

| Tarea | Quién | Condición de ciego |
|---|---|---|
| Verificación del juez (20 % de las respuestas juzgadas, una corrida sorteada por pregunta y condición; unas 240 filas) | `gv` | No abre la clave (condición, corrida, veredicto del juez); no ha visto las cifras del Experimento B. Guía: [`verificacion-juez-humano.md`](../anotacion/verificacion-juez-humano.md) |
| Validación manual de la alineación (100 pares) | `gv` | No abre la clave; no ha visto las cifras del Experimento A |
| Etapa de las fallas de C2 en E1 (OE4; hasta 75 filas) | `gm` | Etiqueta antes de ver el resumen; la pista automática no es una etiqueta. Guía: [`etapa-oe4.md`](../anotacion/etapa-oe4.md) |

`jss` no etiqueta ninguna de las tres, porque adjudicó la referencia y corre los experimentos.

**Kappa indefinido.** En la verificación del juez, un kappa indefinido en `outdated` o en `evidence_supported` (juez y personas usan una sola clase) cuenta como «no cumple», como ya lo hacía `correct`: se informa el acuerdo observado y la prevalencia, esa métrica se reporta solo con la evaluación humana o marcada como no confiable, y no se interpreta como acuerdo.

### 6. Fallas y repeticiones

Reanudar una corrida con el mismo `--run-name`, reiniciar Ollama o reintentar los errores no exige un congelamiento nuevo ni viola el protocolo. Una corrida abandonada y reiniciada con otro nombre se declara en el notebook con el motivo. Las respuestas `judge_failure` no se reintentan. Detalle: [Fallas y repeticiones](../protocols/congelamiento.md#fallas-y-repeticiones).

### 7. Código y registro

El commit exacto desde el que se corre es **el commit de fusión del PR de este ADR en `main`**. Se registra con `uv run afg freeze write --adr 0023`, ejecutado sobre `main` justo después de esa fusión, en un PR posterior que agrega solo `config/freeze.json`. **La fuente de verdad es ese registro, no este texto.** El `config/freeze.json` del ADR 0022 se elimina en el PR de este ADR: ya no valida con el esquema 2, y mientras no exista el nuevo el bloqueo impide cualquier corrida sobre evaluación.

### 8. Regla

**Nada de lo congelado cambia sin un ADR nuevo.** El resto de la regla del ADR 0022 sigue igual: `afg experiment a`, `a-batch`, `a-relations`, `afg c3 build` y `afg experiment b` corren sobre una serie de evaluación solo si el registro existe, la serie está en él y nada difiere; las series de desarrollo (ES2015, IS1004, TS3009) corren sin registro y una serie sin partición en `config/corpus.toml` nunca corre. Se heredan las cifras de la referencia del ADR 0022: recall del bloqueador 0,407 ([ADR 0020](0020-adr-se-mantiene-el-bloqueador-lexico.md)) y 24 preguntas de E3 ([ADR 0021](0021-adr-minimo-de-e3-segun-relaciones-disponibles.md)).

## Consecuencias

- **Ninguna cifra cambia**: no existía ninguna corrida y la referencia, el banco y los valores de configuración son los del ADR 0022.
- **Más personas-horas conocidas antes de correr.** Quedan nombradas tres tareas humanas con su rol y su ciego; los tiempos no están medidos y las estimaciones de las guías son de referencia.
- **Un informe se puede negar por una diferencia de código**, lo que protege contra mezclar una corrida con otra versión. Una corrida hecha con el registro ya presente no se rechaza, porque el registro no es código.
- **El cierre de #237** lo hace el PR del registro, con las 14 series en él.

## Respaldo

- Código: `src/afg/experiments/freeze.py` (`build_freeze_record`, `read_freeze_record`, `freeze_differences`, `gate_partition`, `freeze_provenance`, `manifest_series`), `analysis.py`, `c2_base_evidence.py`, `oe4_summary.py`, `runner.py`, `extraction_batch.py`, `src/afg/evaluation/judge_human_check.py` y `src/afg/extraction/openkos/gold_bundle.py` (PR #283).
- Tests: `tests/test_freeze.py`, `tests/test_cli_freeze_gate.py`, `tests/test_experiment_b_analysis.py`, `tests/test_cli_experiment_b_oe4_sheet.py`, `tests/test_oe4_summary.py` y `tests/test_c3_gold_bundle.py`, entre otros.
- Protocolo: [`docs/protocols/congelamiento.md`](../protocols/congelamiento.md).
- Guías para las personas: [`verificacion-juez-humano.md`](../anotacion/verificacion-juez-humano.md), [`etapa-oe4.md`](../anotacion/etapa-oe4.md) y [`validacion-manual-alineacion.md`](../anotacion/validacion-manual-alineacion.md).
- Registro: `config/freeze.json`, que se agrega en el PR posterior a la fusión de este ADR.
