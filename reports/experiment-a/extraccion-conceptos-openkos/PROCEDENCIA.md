# Extracción de conceptos en OpenKOS: procedencia

Copia de los archivos de puntaje **agregados** de tres evaluaciones prerregistradas que
OpenKOS hizo sobre su extracción de conceptos. Los lee el
[notebook 18](../../../notebooks/18-jss-extraccion-de-conceptos-openkos.ipynb) con
`src/afg/experiments/concept_extraction.py`. No hay corridas crudas, respuestas de modelos,
transcripciones ni texto de la referencia.

| Campo | Valor |
|---|---|
| Origen | `~/Dev/Projects/openkos-eval-runs/concept-screen/` y `~/Dev/Projects/openkos-eval-runs/window-screen/` (fuera de ambos repositorios) |
| Copiado | 2026-10-19 |
| Prerregistros | `evals/concept_model_screen/PREREGISTRATION.md` (#1567, para #1557), `evals/concept_model_screen/DROP_ABLATION_PREREGISTRATION.md` (#1574, para #1572), `evals/concept_window_screen/PREREGISTRATION.md` (#1573, para #1558), todos fusionados en OpenKOS antes de la primera corrida puntuada |
| Informes | `evals/concept_model_screen/RESULTS.md`, `DROP_ABLATION_RESULTS.md` y `evals/concept_window_screen/RESULTS.md` en OpenKOS |
| Commit del arnés | `ebbde16f` (#1557), `90563cab` (puntaje de #1572), `7f0a7689` (#1558) |
| Reuniones puntuadas | ES2015a, ES2015d, IS1004b, IS1004d, TS3009c: **solo desarrollo** ([ADR 0005](../../../docs/decisions/0005-adr-development-evaluation-split.md)). El cargador rechaza cualquier otra |
| Fechas de las corridas | 2026-10-18 y 2026-10-19 |

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

## Política de datos

Los JSON son puntajes agregados (coberturas, intervalos, conteos y tiempos) sobre series de
desarrollo, y se versionan para que el notebook se pueda releer sin rehacer nada (unos
170 KB). La lista de descartes de #1572 trae, en el original, los títulos y descripciones que
escribió el modelo a partir de transcripciones de AMI; OpenKOS los mantiene fuera de su
repositorio, y aquí tampoco se copiaron: el notebook solo necesita los conteos por tipo y
clase.
