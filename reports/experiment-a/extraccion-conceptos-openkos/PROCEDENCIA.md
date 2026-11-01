# Extracción de conceptos en OpenKOS: procedencia

Copia de los archivos de puntaje **agregados** de las evaluaciones prerregistradas que
OpenKOS hizo sobre su extracción de conceptos, sobre los modelos de su consulta (*Ask*) y
sobre su entorno de ejecución local. Los lee el
[notebook 18](../../../notebooks/18-jss-extraccion-de-conceptos-openkos.ipynb) con
`src/afg/experiments/concept_extraction.py`. No hay corridas crudas, respuestas de modelos,
transcripciones ni texto de la referencia.

| Campo | Valor |
|---|---|
| Origen | `~/Dev/Projects/openkos-eval-runs/concept-screen/`, `window-screen/`, `judge-study/`, `ask-screen/` (incluida `ask-screen/swap-measure/`) y `runtime-screen/` (fuera de ambos repositorios) |
| Copiado | 2026-10-19 y 2026-10-20 (en orden de llegada de los resultados) |
| Prerregistros | `evals/concept_model_screen/PREREGISTRATION.md` (#1567, para #1557), `evals/concept_model_screen/DROP_ABLATION_PREREGISTRATION.md` (#1574, para #1572), `evals/concept_window_screen/PREREGISTRATION.md` (#1573, para #1558), `evals/concept_model_screen/JUDGE_STUDY_PREREGISTRATION.md` (#1578, para #1571), `evals/ask_model_screen/PREREGISTRATION.md` (#1582, para #1560), la barra de ADR-0076 (fijada en `e1f8cbfd`, para #1585), `evals/runtime_screen/PREREGISTRATION.md` (#1588, para #1586 y #1587), todos fusionados en OpenKOS antes de la primera corrida puntuada |
| Informes | `evals/concept_model_screen/RESULTS.md`, `DROP_ABLATION_RESULTS.md`, `JUDGE_STUDY_RESULTS.md` (#1580), `evals/concept_window_screen/RESULTS.md` `evals/ask_model_screen/RESULTS.md` (#1584), `docs/adr/0076-…` (#1585) y `evals/runtime_screen/RESULTS.md` (#1589) en OpenKOS |
| Commit del arnés | `ebbde16f` (#1557), `90563cab` (puntaje de #1572), `7f0a7689` (#1558), `c8f3daf9` (#1571), `a32a429c` (#1560, el registro; el arnés no cambió después), `30ff7774` (#1586 y #1587) |
| Reuniones puntuadas | ES2015a, ES2015d, IS1004b, IS1004d, TS3009c: **solo desarrollo** ([ADR 0005](../../../docs/decisions/0005-adr-development-evaluation-split.md)). El cargador rechaza cualquier otra. El estudio del juez (#1571) reutiliza esas mismas corridas de #1557 y su archivo solo trae agregados por extractor, sin identificadores de reunión. El *screen* de Ask (#1560) no usa AMI: solo documentos sintéticos del repositorio de OpenKOS |
| Fechas de las corridas | 2026-10-18 y 2026-10-19 (el juez de #1571, 11:46 a 12:09; Ask, #1560, 13:07 a 16:11; barra de ADR-0076, 17:28 a 17:38; entorno de ejecución, 18:43 a 22:29) |

## Contenido

| Archivo | Origen | sha256 del original | Copia |
|---|---|---|---|
| `model-screen/r1.json` | `concept-screen/scores/r1.json` | `e4986dd9…` | sin modificar |
| `model-screen/r2.json` | `concept-screen/scores/r2.json` | `718252c2…` | sin modificar |
| `model-screen/validity.json` | `concept-screen/scores/validity.json` | `5ee4712a…` | sin modificar |
| `model-screen/stage0.json` | `concept-screen/stage0.json` | `15f6fda9…` | sin modificar |
| `model-screen/decisions/r1-1.json` | `concept-screen/decisions/r1-1.json` | `23687c34…` | sin modificar |
| `model-screen/decisions/r2-2.json` | `concept-screen/decisions/r2-2.json` | `4a12bd9e…` | sin modificar |
| `model-screen/decisions/validity-validity.json` | `concept-screen/decisions/validity-validity.json` | `e2b04117…` | sin modificar |
| `drop-ablation/drop_ablation.json` | `concept-screen/scores/drop_ablation.json` | `555ae41b…` | sin modificar |
| `drop-ablation/drop_ablation_classes.json` | `concept-screen/scores/drop_ablation_classes.json` | `473f69af…` | **reducida**: se quitaron `title`, `description` y `body_chars` de cada fila; quedan regla, reunión, corrida, tipo, ventana, modelo y clase |
| `window-screen/w8b.json` | `window-screen/scores/w8b.json` | `fa89b521…` | sin modificar |
| `window-screen/stage0.json` | `window-screen/stage0.json` | `b91cfad9…` | sin modificar |
| `window-screen/decisions/w8b.json` | `window-screen/decisions/w8b.json` | `37894d50…` | sin modificar |
| `judge-study/judge_study.json` | `judge-study/scores/judge_study.json` | `a3457d0e…` | sin modificar (puntajes por brazo y extractor, y el veredicto del arnés) |
| `ask-screen/round1.json` | `ask-screen/compare-runs1-qwen3-8b.json` | `d40262b5…` | renombrado, contenido sin modificar |
| `ask-screen/round2.json` | `ask-screen/compare-runs2-qwen3-8b.json` | `5a1fd6d7…` | renombrado, contenido sin modificar |
| `ask-screen/confirmation.json` | `ask-screen/compare-runs5-from11-qwen3-8b.json` | `ecef44bd…` | renombrado, contenido sin modificar |
| `ask-screen/swap-measure.json` | `ask-screen/swap-measure/results.json` | `1a8f15f9…` | renombrado, contenido sin modificar (tiempos por pregunta y `ollama ps`) |
| `runtime-screen/floor/floor-A-results.json` | `runtime-screen/floor-A/results.json` | `c36f7a0d…` | renombrado, sin modificar |
| `runtime-screen/floor/floor-A-verdict.json` | `runtime-screen/floor-A/verdict.json` | `e31717a7…` | renombrado, sin modificar |
| `runtime-screen/floor/floor-B-results.json` | `runtime-screen/floor-B/results.json` | `52def34a…` | renombrado, sin modificar |
| `runtime-screen/floor/floor-B-verdict.json` | `runtime-screen/floor-B/verdict.json` | `1fdee257…` | renombrado, sin modificar |
| `runtime-screen/stage1/stage1-verdict.json` | `runtime-screen/stage1/stage1-verdict.json` | `4f240797…` | sin modificar |
| `runtime-screen/stage1/embed-check.json` | `runtime-screen/stage1/embed-check.json` | `ccb32333…` | sin modificar |
| `runtime-screen/stage1/perf-summary.json` | `runtime-screen/stage1/perf-{ollama,llama.cpp,mlx}-{qwen3-8b,gemma4-26b-a4b}.json` (`51a78058…`, `ddf92eeb…`, `367f2526…`, `abd2036e…`, `128d3619…`, `14376981…`) | — | **derivado**: por entorno y modelo, el `summary`, las cargas, las velocidades de cliente y el *digest*; sin `server_argv`, rutas locales ni procesos. Se omitió el intento rechazado de MLX con KV cuantizada |
| `runtime-screen/stage1/swap-summary.json` | `runtime-screen/stage1/swap-{ollama,llama.cpp,mlx}.json` (`fce29799…`, `a2ab3351…`, `2c7b5fb7…`) | — | **derivado**: tiempos de cada cambio y su mediana; el destino queda como nombre de modelo, sin ruta local ni `ollama ps` |
| `runtime-screen/ask/ask-qwen3-8b.json` | `runtime-screen/compare/ask-qwen3-8b.json` | `c35b4269…` | sin modificar |
| `runtime-screen/ask/ask-gemma4-26b-a4b.json` | `runtime-screen/compare/ask-gemma4-26b-a4b.json` | `21f396f0…` | sin modificar |
| `runtime-screen/concept/runtime-both.json` | `runtime-screen/concept-replay/scores/runtime-both.json` | `0cbf16c4…` | sin modificar; sus reuniones (ES2015a, ES2015d, IS1004b, IS1004d, TS3009c) pasan por la guarda de series |

## Política de datos

Los JSON son puntajes agregados (coberturas, intervalos, conteos y tiempos) sobre series de
desarrollo, y se versionan para que el notebook se pueda releer sin rehacer nada (unos
170 KB). La lista de descartes de #1572 trae, en el original, los títulos y descripciones que
escribió el modelo a partir de transcripciones de AMI; OpenKOS los mantiene fuera de su
repositorio, y aquí tampoco se copiaron: el notebook solo necesita los conteos por tipo y
clase. De #1560 se copiaron solo los informes de comparación (deltas, intervalos, tasas de
los vetos y penalizaciones); las respuestas generadas, los contextos y las corridas
(`runs/`, `generations/`, `contexts.json`) se quedaron fuera, y los informes copiados no
contienen texto escrito por un modelo. De la barra de ADR-0076 y de #1587 se copiaron solo
los tiempos (las respuestas `a-*.txt` y `b-*.txt` se quedaron fuera), y de #1586 ni pesos
(39 GB), ni registros de servidor, ni cachés, ni generaciones.
